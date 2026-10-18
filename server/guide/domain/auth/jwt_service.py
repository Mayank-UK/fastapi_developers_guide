"""The token engine: HS256 JWTs — mint with claims, verify with verdicts.

``TokenService`` is PyJWT behind the domain's vocabulary. ``mint``
builds the claim set a production token carries (``sub`` the subject,
``iat``/``exp`` the validity window, ``nbf`` the not-before, ``iss``
the issuer, ``scopes`` the authority, ``jti`` a unique id) and signs it
HS256 with the configured secret; the ``sign_with="wrong"`` option is
the lab's attacker — the same claims signed by a DIFFERENT secret, so
the invalid-signature path is a real forged token, not hand-edited
bytes. ``verify`` classifies every way verification can end — valid,
expired, not-yet-valid, bad-signature, malformed — by catching PyJWT's
exception family in order, signature first: a forged token fails as a
forgery even if its claims would also have expired.

``login`` is the OAuth2 password flow's server half: credentials in
(the router parses FastAPI's login FORM), one bearer token out — the
``OAuth2PasswordBearer`` dependency then carries that token back on
protected calls. The trade is taught where it is made: the token is
SELF-carrying (no store consulted at verify) which makes verification
stateless and fast and revocation approximate — expiry is the only
lever, which is exactly what the refresh-rotation engine exists to fix.
"""

from datetime import UTC, datetime
from typing import Final
from uuid import uuid4

import jwt as pyjwt
import structlog

from guide.core.errors import AppError, FailureKind
from guide.domain.auth.password_service import PasswordService
from guide.domain.auth.ports import (
    ACCESS_TOKEN_TTL_SECONDS,
    MintedTokenRow,
    MintTokenRequest,
    TokenLoginRow,
    TokenOutcome,
    TokenVerifyRow,
    UserDirectory,
)

logger = structlog.get_logger()

TOKEN_ISSUER: Final = "guide.demo"
"""The ``iss`` claim every minted token carries — and the one verify demands."""

TOKEN_ALGORITHM: Final = "HS256"
"""Symmetric signing: one secret signs and verifies (RS256 splits the pair)."""

WRONG_SECRET: Final = "attacker-secret-that-the-server-does-not-know"
"""The lab's forgery key — signs structurally-valid tokens the server rejects."""

STATELESS_NOTE: Final = (
    "verification consults nothing but the signature and the claims: no store, "
    "no session, no round trip — stateless and fast, and revocation is "
    "approximate (expiry is the only lever)"
)
"""The statelessness trade, stated where the suite can pin it."""


def _utcnow() -> datetime:
    """One clock seam — tests inject determinism by monkeypatching time."""
    return datetime.now(UTC)


def _as_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value, tz=UTC)


class TokenService:
    """Mint, login, verify — HS256 over one configured secret."""

    def __init__(self, secret: str, directory: UserDirectory, passwords: PasswordService) -> None:
        self._secret = secret
        self._directory = directory
        self._passwords = passwords

    def mint(
        self, request: MintTokenRequest, *, now: datetime | None = None
    ) -> MintedTokenRow:
        """Build the claim set, sign it, and answer token + decoded anatomy.

        Timestamps are seconds-since-epoch (the JWT register's rule), and
        the clock is injectable: tests mint expired / not-yet-valid tokens
        with explicit times, never sleeps.
        """
        moment = now or _utcnow()
        iat = int(moment.timestamp())
        expires_at_timestamp = iat + request.ttl_seconds
        payload: dict[str, object] = {
            "sub": request.username,
            "iat": iat,
            "exp": expires_at_timestamp,
            "nbf": iat + request.not_before_seconds,
            "iss": TOKEN_ISSUER,
            "scopes": list(request.scopes),
            "jti": str(uuid4()),
        }
        secret = self._secret if request.sign_with == "real" else WRONG_SECRET
        token = pyjwt.encode(payload, secret, algorithm=TOKEN_ALGORITHM)
        header = {"alg": TOKEN_ALGORITHM, "typ": "JWT"}
        logger.info("token_minted", sub=request.username, signed_with=request.sign_with)
        return MintedTokenRow(
            token=token,
            header=header,
            payload=payload,
            signed_with=request.sign_with,
            expires_at=_as_datetime(expires_at_timestamp).isoformat(timespec="milliseconds"),
            detail=(
                f"minted for {request.username}: three dots-joined parts — "
                f"{header['alg']} header, {request.username}'s claims (sub, iat, exp, "
                f"nbf, iss, scopes, jti), and a signature over both — signed with the "
                f"{'server' if request.sign_with == 'real' else 'WRONG (attacker)'} "
                "secret"
            ),
        )

    def mint_scoped(self, username: str, scopes: list[str], ttl_seconds: int) -> MintedTokenRow:
        """Mint for the engines that follow (OAuth exchange, refresh rotation):
        the standard claim set, the standard secret, a caller-chosen lease."""
        return self.mint(
            MintTokenRequest(username=username, scopes=scopes, ttl_seconds=ttl_seconds)
        )

    async def login(self, username: str, password: str) -> TokenLoginRow:
        """The OAuth2 password flow: credentials in, bearer token out.

        Same timing-uniform credential check as the session engine — an
        unknown user burns the decoy hash and answers identically.
        """
        user = await self._directory.find_user(username)
        if user is None:
            self._passwords.verify_uniform(None, password)
            raise AppError(FailureKind.UNAUTHORIZED, "invalid credentials")
        if not self._passwords.verify_uniform(user.password_hash, password):
            raise AppError(FailureKind.UNAUTHORIZED, "invalid credentials")
        minted = self.mint(
            MintTokenRequest(username=user.username, scopes=list(user.scopes))
        )
        return TokenLoginRow(
            access_token=minted.token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(user.scopes),
            username=user.username,
            detail=(
                f"login form accepted for {user.username}: the token carries "
                f"{ACCESS_TOKEN_TTL_SECONDS}s of life and the scopes {' '.join(user.scopes)}; "
                "send it back as the Authorization: Bearer header and every "
                "protected route verifies it statelessly"
            ),
        )

    def verify(self, token: str) -> TokenVerifyRow:
        """Classify a token: valid, expired, not-yet-valid, bad-signature, malformed.

        PyJWT raises by specificity; catching signature failures before the
        claim family keeps a forged-and-expired token honestly labeled a
        FORGERY. Every verdict names its outcome; none leaks the secret.
        Deterministic time tests live at MINT (an explicit ``now`` bakes the
        claims); verification reads the claims with the real clock.
        """
        try:
            payload = pyjwt.decode(
                token,
                self._secret,
                algorithms=[TOKEN_ALGORITHM],
                issuer=TOKEN_ISSUER,
                options={"require": ["sub", "exp", "iat", "nbf", "iss"]},
            )
        except pyjwt.InvalidSignatureError:
            return self._verdict(
                "bad-signature",
                "the signature does not match the server's secret — a forged "
                "or tampered token",
            )
        except pyjwt.ExpiredSignatureError:
            return self._verdict(
                "expired", "the exp claim is in the past — the token's lease ran out"
            )
        except pyjwt.ImmatureSignatureError:
            return self._verdict(
                "not-yet-valid", "the nbf claim is in the future — not valid YET"
            )
        except pyjwt.MissingRequiredClaimError:
            return self._verdict(
                "malformed", "a required claim (sub, exp, iat, nbf, iss) is missing"
            )
        except pyjwt.InvalidTokenError:
            return self._verdict(
                "malformed", "not decodable as a signed JWT — wrong shape or garbage"
            )
        scopes = tuple(payload.get("scopes") or ())
        username = str(payload["sub"])
        logger.info("token_verified", sub=username)
        return TokenVerifyRow(
            outcome="valid",
            username=username,
            scopes=scopes,
            expires_at=_as_datetime(int(payload["exp"])).isoformat(timespec="milliseconds"),
            detail=(
                f"signature verified against the server secret and every claim holds: "
                f"{username}, scopes {', '.join(scopes) or 'none'}, exp in the future, "
                "nbf in the past — nothing was consulted but the token itself"
            ),
        )

    def require(self, token: str | None) -> tuple[str, tuple[str, ...]]:
        """The protected-endpoint check: caller + scopes, or the 401 envelope.

        ``verify`` classifies for the panel; ``require`` enforces: every
        outcome except valid is one unauthorized — the message names the
        classification (expired, not-yet-valid, …) because that is safe
        to tell a token-holder, and never includes the secret.
        """
        if token is None:
            raise AppError(FailureKind.UNAUTHORIZED, "not authenticated — missing bearer token")
        verdict = self.verify(token)
        if verdict.outcome != "valid" or verdict.username is None or verdict.scopes is None:
            raise AppError(FailureKind.UNAUTHORIZED, f"invalid token — {verdict.outcome}")
        return verdict.username, verdict.scopes

    @staticmethod
    def _verdict(outcome: TokenOutcome, reason: str) -> TokenVerifyRow:
        """One failed verification as a row — classification, no secrets."""
        logger.info("token_rejected", outcome=outcome)
        return TokenVerifyRow(
            outcome=outcome, username=None, scopes=None, expires_at=None, detail=reason
        )
