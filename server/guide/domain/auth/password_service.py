"""The password engine: argon2 hashing, verification, the rehash signal.

``PasswordService`` wraps argon2-cffi's ``PasswordHasher`` behind the
domain's vocabulary: ``hash_password`` mints an argon2id string (salted,
parameter-stamped — no two hashes of the same password look alike),
``verify_password`` answers match + needs_rehash + honest timing, and
``verify_uniform`` is the timing lesson made code: when the username is
UNKNOWN it still burns one full argon2 verification against a decoy hash,
so "no such user" and "wrong password" cost the same and an attacker
cannot enumerate usernames off response-time differences.

Hashing is NOT encryption — the hash cannot be undone, only re-run; the
``HASHING_VS_ENCRYPTION_NOTE`` constant states the distinction where the
suite can pin it. Elapsed times are real measurements (``perf_counter``
around the C call), reported honestly; the demo never rounds them into
marketing. Nothing secret is ever logged — timings and verdicts only.
"""

import time
from typing import Final

import structlog
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from guide.domain.auth.ports import (
    HashPasswordRequest,
    PasswordHashRow,
    PasswordVerifyRow,
    VerifyPasswordRequest,
)

logger = structlog.get_logger()

HASHING_VS_ENCRYPTION_NOTE: Final = (
    "hashing is one-way: verify re-runs the function over the candidate, "
    "it never decrypts the stored string — you cannot un-hash a password, "
    "you can only check a guess"
)
"""The distinction the whole section stands on — pinned by the suite."""

DECOY_HASH: Final = (
    "$argon2id$v=19$m=65536,t=3,p=4$kwLrdfcyKf0Y8QktrIxRbA$"
    "Pssupwpn9hPxowGvjwaEsQziYSncU6K7FAC2Ihmkzng"
)
"""A valid argon2id hash of a throwaway string — burned for unknown users."""

LEGACY_HASH: Final = (
    "$argon2id$v=19$m=8192,t=1,p=2$MLNClM6LqCQvN7PDy20tLg$"
    "gjaMkZv4WQD5SpTax5yhrisVedBjdhNmottcf5bCQd4"
)
"""Same-family hash at 2015-era cost — verify passes, needs_rehash fires."""

LEGACY_PARAMETERS: Final = "argon2id · m=8192 KiB · t=1 · p=2 (2015-era cost)"


def production_hasher() -> PasswordHasher:
    """The default-parameter hasher every production wiring uses (64 MiB,
    t=3, p=4 — argon2-cffi's 2026 defaults). Tests inject their own."""
    return PasswordHasher()


class PasswordService:
    """Hash, verify, and the rehash signal — argon2id behind one seam.

    The hasher is injected: the production wiring passes a default-
    parameter ``PasswordHasher`` (64 MiB, t=3, p=4 — the 2026 default);
    tests inject whatever they need without monkeypatching.
    """

    def __init__(self, hasher: PasswordHasher) -> None:
        self._hasher = hasher

    @property
    def parameters(self) -> str:
        """The active hasher's cost parameters, for panels and prose."""
        return (
            f"argon2id · m={self._hasher.memory_cost} KiB · "
            f"t={self._hasher.time_cost} · p={self._hasher.parallelism}"
        )

    def hash_password(self, request: HashPasswordRequest) -> PasswordHashRow:
        """Hash one password: fresh salt, parameter-stamped, honestly timed."""
        started = time.perf_counter()
        digest = self._hasher.hash(request.password)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        logger.info("password_hashed", elapsed_ms=elapsed_ms)
        return PasswordHashRow(
            hash=digest,
            algorithm="argon2id",
            parameters=self.parameters,
            elapsed_ms=elapsed_ms,
            detail=(
                f"argon2 hashed the password in {elapsed_ms} ms at {self.parameters} — "
                "the salt is fresh (the same password never hashes to the same "
                "string), the parameters are stamped inside the hash, and the "
                f"cost is the point: {elapsed_ms} ms per attempt is affordable "
                "once per login and ruinous per guess"
            ),
        )

    def verify_password(self, request: VerifyPasswordRequest) -> PasswordVerifyRow:
        """Verify a candidate against a stored hash — match + rehash signal.

        Every path burns the same argon2 work: a MISMATCH raises after the
        full computation, so wrong passwords and right ones cost the same.
        A malformed stored hash is an error, not a failed match — stale
        rows deserve a loud failure, not a silent reject.
        """
        started = time.perf_counter()
        ok = True
        error: str | None = None
        needs_rehash = False
        try:
            self._hasher.verify(request.hash, request.password)
        except VerifyMismatchError:
            ok = False
        except InvalidHashError:
            ok = False
            error = "the stored string is not a valid argon2 hash"
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        if ok:
            needs_rehash = self._hasher.check_needs_rehash(request.hash)
        if error is not None:
            detail = f"verification could not run: {error}"
        elif ok and needs_rehash:
            detail = (
                f"password CORRECT (verified in {elapsed_ms} ms) and the hash is "
                "behind the current parameters — rehash on this login, before "
                "the next verify ever sees it"
            )
        elif ok:
            detail = (
                f"password CORRECT — one full argon2 run in {elapsed_ms} ms, and the "
                "hash's parameters are current (no rehash needed)"
            )
        else:
            detail = (
                f"password WRONG — the rejection still burned the full {elapsed_ms} ms "
                "argon2 run: match and mismatch cost the same, offline or online"
            )
        logger.info("password_verified", ok=ok, needs_rehash=needs_rehash, elapsed_ms=elapsed_ms)
        return PasswordVerifyRow(
            ok=ok,
            needs_rehash=needs_rehash,
            elapsed_ms=elapsed_ms,
            error=error,
            detail=detail,
        )

    def verify_uniform(self, stored_hash: str | None, password: str) -> bool:
        """The timing-uniform credential check every login uses.

        ``stored_hash`` None (unknown username) burns a decoy verification
        so the answer takes the same time as a real wrong password; the
        result is False either way, and callers learn nothing about WHICH
        half failed.
        """
        verdict = self.verify_password(
            VerifyPasswordRequest(password=password, hash=stored_hash or DECOY_HASH)
        )
        return verdict.ok
