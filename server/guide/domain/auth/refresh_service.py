"""The refresh engine: rotating one-time tokens in detectable families.

``RefreshRotationService`` builds the pattern production OAuth2 servers
adopted after tokens lived long enough to be stolen: every login starts
a FAMILY; every exchange CONSUMES the presented refresh token (one-time
use) and issues the next link in the same family; and a presented token
that is ALREADY used is not an error to forgive — it is theft in
progress. Two honest parties never present the same refresh token
twice: the client rotates on receipt, the old value is dead. So the
second presentation means a copy exists in someone else's hands, and
the only safe response is to kill the ENTIRE family — every token in
the chain, current and future — and force a fresh login.

The proof is deterministic and store-side: the family row flips to
revoked, every token row flips with it, and the panel shows the
positions (used, used, revoked…) as a timeline of the rotation. Tokens
are opaque high-entropy handles stored as SHA-256 hashes — the raw
value rides exactly one response (the exchange that minted it), and the
reuse detector works entirely on hashes.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Final

import structlog

from guide.core.errors import AppError, FailureKind
from guide.domain.auth.jwt_service import TokenService
from guide.domain.auth.password_service import PasswordService
from guide.domain.auth.ports import (
    ACCESS_TOKEN_TTL_SECONDS,
    REFRESH_TTL_SECONDS,
    RefreshExchangeRequest,
    RefreshExchangeRow,
    RefreshLoginRequest,
    RefreshLoginRow,
    RefreshStore,
    StoredRefreshFamily,
    StoredRefreshToken,
    UserDirectory,
)

logger = structlog.get_logger()

REFRESH_TOKEN_BYTES: Final = 32
"""The opaque handle's entropy — unguessable, unverifiable without the store."""

REUSE_NOTE: Final = (
    "a refresh token is one-time: presenting it again means a copy left the "
    "rightful client, so the whole family dies — rotation plus reuse detection "
    "turns a stolen token into an ALARM instead of a skeleton key"
)
"""The pattern's thesis, stated where the suite can pin it."""


def hash_refresh_token(token: str) -> str:
    """SHA-256 at rest — same discipline as API keys, same reasoning."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    """One clock seam — tests inject determinism by monkeypatching time."""
    return datetime.now(UTC)


class RefreshRotationService:
    """Login starts a family; exchange rotates; reuse revokes everything."""

    def __init__(
        self,
        store: RefreshStore,
        directory: UserDirectory,
        passwords: PasswordService,
        tokens: TokenService,
    ) -> None:
        self._store = store
        self._directory = directory
        self._passwords = passwords
        self._tokens = tokens
        self.logins = 0
        self.rotations = 0
        self.reuse_events = 0

    async def login(self, request: RefreshLoginRequest) -> RefreshLoginRow:
        """Verify credentials, start family #1: one refresh token, raw once."""
        user = await self._directory.find_user(request.username)
        if user is None:
            self._passwords.verify_uniform(None, request.password)
            raise AppError(FailureKind.UNAUTHORIZED, "invalid credentials")
        if not self._passwords.verify_uniform(user.password_hash, request.password):
            raise AppError(FailureKind.UNAUTHORIZED, "invalid credentials")

        moment = _utcnow()
        family_id = f"fam_{secrets.token_urlsafe(8)}"
        refresh_token = f"rt_{secrets.token_urlsafe(REFRESH_TOKEN_BYTES)}"
        await self._store.start_family(
            StoredRefreshFamily(
                family_id=family_id,
                username=user.username,
                status="active",
                created_at=moment.isoformat(timespec="milliseconds"),
            ),
            StoredRefreshToken(
                token_hash=hash_refresh_token(refresh_token),
                family_id=family_id,
                position=1,
                status="active",
                issued_at=moment.isoformat(timespec="milliseconds"),
                used_at=None,
            ),
        )
        access = self._tokens.mint_scoped(
            username=user.username, scopes=list(user.scopes), ttl_seconds=ACCESS_TOKEN_TTL_SECONDS
        )
        self.logins += 1
        logger.info("refresh_family_started", family_id=family_id)
        return RefreshLoginRow(
            family_id=family_id,
            username=user.username,
            access_token=access.token,
            access_expires_in=ACCESS_TOKEN_TTL_SECONDS,
            refresh_token=refresh_token,
            detail=(
                f"family {family_id} born at position 1: an access token "
                f"({ACCESS_TOKEN_TTL_SECONDS}s) and the first refresh token — the "
                "raw refresh value appears HERE and nowhere else; the store keeps "
                f"only {hash_refresh_token(refresh_token)[:12]}…, its SHA-256"
            ),
        )

    async def exchange(self, request: RefreshExchangeRequest) -> RefreshExchangeRow:
        """Present one refresh token: rotate it, or die loudly on reuse.

        Three store-backed outcomes: ACTIVE token → mark used, mint the
        next link (rotation); USED token → REUSE — revoke the whole
        family, answer with the kill count as proof; anything else
        (unknown hash, revoked family) → invalid, the 401 envelope. The
        ordered awaits make the sequence testable with no sleeps.
        """
        presented_hash = hash_refresh_token(request.refresh_token)
        stored = await self._store.find_token(presented_hash)
        if stored is None:
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "invalid refresh token — unknown handle (families are per-user; "
                "login mints one)",
            )
        if stored.status == "revoked":
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "invalid refresh token — this family was revoked after a reuse "
                "event; log in again to start a new one",
            )
        if _utcnow() >= datetime.fromisoformat(stored.issued_at) + timedelta(
            seconds=REFRESH_TTL_SECONDS
        ):
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "invalid refresh token — the 24h lease ran out; log in again",
            )
        if stored.status == "used":
            killed = await self._store.revoke_family(stored.family_id)
            self.reuse_events += 1
            logger.warning(
                "refresh_reuse_detected",
                family_id=stored.family_id,
                family_tokens_revoked=killed,
            )
            return RefreshExchangeRow(
                outcome="reuse-detected",
                family_id=stored.family_id,
                access_token=None,
                access_expires_in=None,
                refresh_token=None,
                rotated_from_position=stored.position,
                family_tokens_revoked=killed,
                detail=(
                    f"REUSE: position {stored.position} of family {stored.family_id} "
                    f"was already spent, so a copy exists somewhere else — the whole "
                    f"family is revoked ({killed} tokens killed, past and future). "
                    "The next exchange from this family fails as invalid; only a "
                    "fresh login starts a new one. This is the alarm working, not "
                    "an error to forgive"
                ),
            )

        moment = _utcnow()
        await self._store.mark_used(presented_hash, moment.isoformat(timespec="milliseconds"))
        next_token = f"rt_{secrets.token_urlsafe(REFRESH_TOKEN_BYTES)}"
        await self._store.add_token(
            StoredRefreshToken(
                token_hash=hash_refresh_token(next_token),
                family_id=stored.family_id,
                position=stored.position + 1,
                status="active",
                issued_at=moment.isoformat(timespec="milliseconds"),
                used_at=None,
            ),
        )
        family = await self._store.find_family(stored.family_id)
        username = family.username if family else stored.family_id
        user = await self._directory.find_user(username)
        scopes = list(user.scopes) if user else []
        access = self._tokens.mint_scoped(
            username=username, scopes=scopes, ttl_seconds=ACCESS_TOKEN_TTL_SECONDS
        )
        self.rotations += 1
        logger.info(
            "refresh_rotated", family_id=stored.family_id, position=stored.position + 1
        )
        return RefreshExchangeRow(
            outcome="rotated",
            family_id=stored.family_id,
            access_token=access.token,
            access_expires_in=ACCESS_TOKEN_TTL_SECONDS,
            refresh_token=next_token,
            rotated_from_position=stored.position,
            family_tokens_revoked=0,
            detail=(
                f"rotated position {stored.position} → {stored.position + 1} in "
                f"family {stored.family_id}: the presented token is now USED "
                "(one-time — presenting it again trips the reuse alarm), and the "
                "next refresh token appears here and nowhere else; the new access "
                f"token is good for {ACCESS_TOKEN_TTL_SECONDS}s"
            ),
        )

    async def families(self) -> list[tuple[StoredRefreshFamily, list[StoredRefreshToken]]]:
        """The panel's roster: every family with its token timeline."""
        return await self._store.list_families()
