"""The API-key engine: readable prefix + high-entropy secret, hashed at rest.

``ApiKeyService`` implements the three rules a key system lives or dies
by. GENERATION mints a two-part key — a short readable prefix (8 hex
chars, greppable in logs and UIs) and a 256-bit secret — and the FULL
key is stored only as its SHA-256 hash, so a leaked database does not
leak working keys. LOOKUP splits a presented key at the dot, fetches
the record by prefix, re-hashes the presentation, and compares the two
hashes with ``hmac.compare_digest`` — constant time, so an attacker
cannot binary-search the hash byte by byte off response timing.
REVOCATION is a prefix-keyed delete: the next lookup finds nothing, the
key is dead instantly, no expiry waiting.

The raw key appears in exactly ONE response: creation. Everything after
— rosters, logs, error details — carries the prefix alone, and even the
prefix is display, never proof.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Final

import structlog

from guide.core.errors import AppError, FailureKind
from guide.domain.auth.ports import (
    API_KEY_PREFIX_BYTES,
    API_KEY_SECRET_BYTES,
    ApiKeyCallRow,
    ApiKeyCreatedRow,
    ApiKeyRevokeRow,
    ApiKeyStore,
    CreateKeyRequest,
    StoredApiKey,
)

logger = structlog.get_logger()

KEY_SEPARATOR: Final = "."
"""The one delimiter between prefix and secret — malformed keys say so."""


def hash_key(full_key: str) -> str:
    """The storage hash: plain SHA-256 — the key's own entropy is the salt.

    Argon2 is for passwords (low entropy, must be slow); a 256-bit random
    key needs no stretching — one SHA-256 makes the grind 2^256 wide.
    """
    return hashlib.sha256(full_key.encode("utf-8")).hexdigest()


DUMMY_KEY_HASH: Final = hash_key("fdg_00000000.dead-key-that-never-existed")
"""A comparison target that never matches — burned on malformed presentations."""

NEVER_STORE_RAW_NOTE: Final = (
    "the key is stored as its SHA-256 hash and the raw value is shown exactly "
    "once, at creation — a leaked store gives an attacker hashes to grind, "
    "not keys to use"
)
"""The storage rule, stated where the suite can pin it."""


class ApiKeyService:
    """Generate, verify (constant-time), revoke — prefix-keyed records."""

    def __init__(self, store: ApiKeyStore) -> None:
        self._store = store

    async def generate(self, request: CreateKeyRequest) -> ApiKeyCreatedRow:
        """Mint prefix + secret, store the hash, answer the raw key ONCE."""
        prefix = f"fdg_{secrets.token_hex(API_KEY_PREFIX_BYTES)}"
        secret = secrets.token_urlsafe(API_KEY_SECRET_BYTES)
        full_key = f"{prefix}{KEY_SEPARATOR}{secret}"
        key_hash = hash_key(full_key)
        await self._store.save_key(
            StoredApiKey(
                prefix=prefix,
                name=request.name,
                scopes=tuple(request.scopes),
                key_hash=key_hash,
                created_at=datetime.now(UTC).isoformat(timespec="milliseconds"),
            )
        )
        logger.info("api_key_created", prefix=prefix)
        return ApiKeyCreatedRow(
            prefix=prefix,
            key=full_key,
            key_hash=key_hash,
            name=request.name,
            scopes=tuple(request.scopes),
            detail=(
                f"generated {prefix} — the prefix is the greppable half, the "
                "secret is 256 bits of unguessable; the store holds "
                f"{key_hash[:12]}… (the SHA-256), and THIS response is the only "
                "place the raw key will ever appear: copy it now, ask again "
                "later and you get a new key"
            ),
        )

    async def verify(self, presented: str) -> StoredApiKey:
        """The protected-call check: prefix lookup + constant-time compare.

        Returns the key's record on success; raises the standard 401
        otherwise. Malformed (no separator) presentations burn one dummy
        hash comparison so every rejection costs the same shape of work.
        """
        if KEY_SEPARATOR not in presented:
            hmac.compare_digest(hash_key(presented), DUMMY_KEY_HASH)
            raise AppError(FailureKind.UNAUTHORIZED, "invalid api key")
        prefix, _secret = presented.split(KEY_SEPARATOR, 1)
        record = await self._store.find_key_by_prefix(prefix)
        presented_hash = hash_key(presented)
        if record is None or not hmac.compare_digest(presented_hash, record.key_hash):
            logger.info("api_key_rejected", prefix=prefix)
            raise AppError(FailureKind.UNAUTHORIZED, "invalid api key")
        logger.info("api_key_accepted", prefix=prefix)
        return record

    async def call(self, presented: str | None) -> ApiKeyCallRow:
        """One authenticated call: what the key's record says it speaks for."""
        if presented is None:
            raise AppError(FailureKind.UNAUTHORIZED, "missing api key — send x-api-key")
        record = await self.verify(presented)
        return ApiKeyCallRow(
            prefix=record.prefix,
            name=record.name,
            scopes=record.scopes,
            detail=(
                f"authenticated as key {record.prefix} ({record.name}) with scopes "
                f"{', '.join(record.scopes)} — the presented key was hashed, looked "
                "up by prefix, and compared in constant time; the raw value was "
                "never stored and is not in this response"
            ),
        )

    async def roster(self) -> list[StoredApiKey]:
        """Every stored record, oldest first — hash previews are display-only."""
        return await self._store.list_keys()

    async def revoke(self, prefix: str) -> ApiKeyRevokeRow:
        """Delete by prefix — instant death for every copy of the key."""
        revoked = await self._store.revoke_key(prefix)
        if not revoked:
            raise AppError(FailureKind.NOT_FOUND, f"no api key with prefix {prefix}")
        logger.info("api_key_revoked", prefix=prefix)
        return ApiKeyRevokeRow(
            prefix=prefix,
            revoked=revoked,
            detail=(
                f"revoked {prefix}: the record is deleted, so the next lookup finds "
                "nothing — revocation is immediate, and every copy of the key in "
                "the world dies with the record"
            ),
        )
