"""The OAuth2 provider: authorization-code + PKCE (S256), in-repo and real.

``OAuthProviderService`` is a teaching authorization server — small, but
every step is the real protocol's shape. ``authorize`` is the front
door: a registered client asks for a code, the request names its
redirect URI and a PKCE code_challenge, the (simulated) resource owner
consents, and the server answers the redirect URL a real client would
follow — code and state in the query string, code bound to client, URI,
and challenge. ``exchange`` is the back door's twin: the client
presents the ONE-TIME code plus the verifier that hashed to the
challenge, the server recomputes S256(verifier), compares in constant
time, burns the code (consumed on FIRST attempt — a failed verifier
still spends it, so codes cannot be ground), and answers an access
token good against the protected resource.

PKCE is the whole point of the section: a public client (no secret on
the machine) proves possession of the verifier only the rightful owner
generated, so an intercepted authorization CODE is worthless — the
exchange fails without the verifier that never traveled the redirect.
``plain`` method is refused: S256 or nothing, because a plaintext
challenge riding the same redirect protects nothing.
"""

import base64
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Final

import structlog

from guide.core.errors import AppError, FailureKind
from guide.domain.auth.jwt_service import TokenService
from guide.domain.auth.ports import (
    ACCESS_TOKEN_TTL_SECONDS,
    CODE_TTL_SECONDS,
    PKCE_VERIFIER_MAX,
    PKCE_VERIFIER_MIN,
    AuthorizationCodeStore,
    AuthorizeRequest,
    AuthorizeRow,
    ExchangeRow,
    PkcePairRow,
    StoredAuthorizationCode,
    TokenExchangeRequest,
)

logger = structlog.get_logger()

CLIENT_ID: Final = "guide-cli"
"""The one registered client — a PUBLIC client: no secret, PKCE required."""

CLIENT_NAME: Final = "Guide CLI (public client)"

REGISTERED_REDIRECT_URIS: Final = ("https://client.example/callback",)
"""Exact-match list: an unregistered redirect_uri is refused, never redirected."""

CLIENT_SCOPES: Final = ("posts:read", "posts:write")
"""The scopes this client may ask consent for."""

PKCE_VERIFIER_BYTES: Final = 48
"""64 base64url characters — inside RFC 7636's 43–128 window."""

CODE_BYTES: Final = 32
"""The authorization code's entropy — high-entropy one-time handles."""

BASE64URL: Final = re.compile(r"^[A-Za-z0-9_-]+$")
"""The code_verifier's alphabet (RFC 7636 §4.1: unreserved ASCII only)."""

PKCE_NOTE: Final = (
    "the verifier never travels the redirect — only its SHA-256 does, so an "
    "intercepted code cannot be exchanged without the secret the rightful "
    "client generated and kept"
)
"""The PKCE guarantee, stated where the suite can pin it."""


def s256_challenge(verifier: str) -> str:
    """RFC 7636 §4.2: base64url(SHA-256(verifier)), padding stripped."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def hash_code(code: str) -> str:
    """Codes are stored hashed too — the same never-store-raw discipline."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    """One clock seam — tests inject determinism by monkeypatching time."""
    return datetime.now(UTC)


class OAuthProviderService:
    """authorize → consent → code → exchange — the code+PKCE grant, whole."""

    def __init__(self, codes: AuthorizationCodeStore, tokens: TokenService) -> None:
        self._codes = codes
        self._tokens = tokens

    def pkce_pair(self) -> PkcePairRow:
        """Generate a verifier/challenge pair — what a client does locally."""
        verifier = secrets.token_urlsafe(PKCE_VERIFIER_BYTES)
        challenge = s256_challenge(verifier)
        return PkcePairRow(
            verifier=verifier,
            code_challenge=challenge,
            method="S256",
            detail=(
                f"verifier ({len(verifier)} chars) stays on the client; only its "
                f"challenge {challenge[:12]}… (S256: base64url of SHA-256, padding "
                "stripped) travels in the authorize request — that one-way trip "
                "is PKCE's entire trick"
            ),
        )

    async def authorize(self, request: AuthorizeRequest) -> AuthorizeRow:
        """Validate the client, the URI, the challenge — issue the one-time code.

        Three hard refusals before anything is issued: an unknown client,
        an unregistered redirect URI (exact match — an open redirect with
        a code attached is a credential leak), and anything but S256. The
        consent is the demo's one simulation: the seeded user ada grants
        the requested scopes, exactly what a real consent screen records.
        """
        if request.client_id != CLIENT_ID:
            raise AppError(
                FailureKind.VALIDATION_FAILED,
                f"unknown client {request.client_id!r} — only {CLIENT_ID!r} is registered",
            )
        if request.redirect_uri not in REGISTERED_REDIRECT_URIS:
            raise AppError(
                FailureKind.VALIDATION_FAILED,
                "redirect_uri is not registered for this client — refusing rather "
                "than redirecting a code somewhere new",
            )
        if not PKCE_VERIFIER_MIN <= len(request.code_challenge) <= PKCE_VERIFIER_MAX:
            raise AppError(
                FailureKind.VALIDATION_FAILED,
                f"code_challenge length must be {PKCE_VERIFIER_MIN}–{PKCE_VERIFIER_MAX} "
                "base64url characters (an S256 digest is 43)",
            )
        moment = _utcnow()
        code = secrets.token_urlsafe(CODE_BYTES)
        await self._codes.issue_code(
            StoredAuthorizationCode(
                code_hash=hash_code(code),
                client_id=request.client_id,
                redirect_uri=request.redirect_uri,
                code_challenge=request.code_challenge,
                code_challenge_method="S256",
                username="ada",
                scopes=CLIENT_SCOPES,
                issued_at=moment.isoformat(timespec="milliseconds"),
                expires_at=(moment + timedelta(seconds=CODE_TTL_SECONDS)).isoformat(
                    timespec="milliseconds"
                ),
            )
        )
        separator = "&" if "?" in request.redirect_uri else "?"
        redirect_to = f"{request.redirect_uri}{separator}code={code}&state={request.state}"
        logger.info("oauth_code_issued", client_id=request.client_id)
        return AuthorizeRow(
            redirect_to=redirect_to,
            state=request.state,
            consent=(
                "consent granted (simulated): ada approved posts:read posts:write for "
                f"{CLIENT_NAME} — a real server renders this screen and records the grant"
            ),
            code_preview=code[:8] + "…",
            expires_in=CODE_TTL_SECONDS,
            detail=(
                f"authorization code issued (one-time, {CODE_TTL_SECONDS}s life) and "
                f"bound to client {CLIENT_ID}, this exact redirect_uri, and the S256 "
                "challenge; the redirect the client follows is shown — the code rides "
                "the front channel, the verifier does not"
            ),
        )

    async def exchange(self, request: TokenExchangeRequest) -> ExchangeRow:
        """Code + verifier → access token. Wrong verifier: dead code, 401.

        The code is consumed FIRST — even a failed exchange spends it.
        That is deliberate: one-time means one ATTEMPT, so an attacker
        who steals the code and guesses verifiers gets exactly one guess
        before the code is ash.
        """
        stored = await self._codes.take_code(hash_code(request.code))
        if stored is None:
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "invalid_grant — the code is unknown, already used, or expired "
                "(one attempt: codes are consumed on first presentation)",
            )
        if not PKCE_VERIFIER_MIN <= len(request.verifier) <= PKCE_VERIFIER_MAX or not (
            BASE64URL.fullmatch(request.verifier)
        ):
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "invalid_grant — the verifier must be 43–128 base64url characters",
            )
        if request.redirect_uri != stored.redirect_uri:
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "invalid_grant — redirect_uri does not match the authorize request",
            )
        if not hmac.compare_digest(s256_challenge(request.verifier), stored.code_challenge):
            logger.info("oauth_pkce_rejected")
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "invalid_grant — S256(verifier) does not match the code_challenge: "
                "wrong verifier, and the code is spent",
            )
        minted = self._tokens.mint_scoped(
            username=stored.username,
            scopes=list(stored.scopes),
            ttl_seconds=ACCESS_TOKEN_TTL_SECONDS,
        )
        logger.info("oauth_exchanged", username=stored.username)
        return ExchangeRow(
            access_token=minted.token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(stored.scopes),
            username=stored.username,
            detail=(
                f"verifier proved (constant-time S256 match), code burned, and the "
                f"access token mints for {stored.username} with "
                f"{', '.join(stored.scopes)} — present it as a Bearer token to the "
                "protected resource and it verifies like any JWT: statelessly"
            ),
        )
