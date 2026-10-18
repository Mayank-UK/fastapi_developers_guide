"""The authentication ports: the identity vocabulary every auth engine speaks.

Six engines live in this package (password, session, api-key, token, OAuth
provider, refresh rotation) and they share one set of store Protocols,
split by substrate: ``UserDirectory`` answers "who is this username"
(the credential halves live with it), ``SessionStore`` keeps server-side
login sessions, ``ApiKeyStore`` keeps hash-only API key records,
``AuthorizationCodeStore`` holds the OAuth authorization server's one-time
codes, and ``RefreshStore`` holds refresh-token families with their
rotation state. The in-memory adapter (``guide.data.auth``) implements
them all on plain dictionaries seeded with pre-hashed argon2 credentials
— the posts-substrate discipline: no new tables, per-app state, honest
stores. Everything here is driver-free and every engine runs on ordered
awaits with no sleeps, so fakes at these boundaries make the security
guarantees (one-time codes, reuse detection, constant-time comparisons)
testable deterministically.

Secrets discipline, stated once for the whole area: RAW keys, tokens and
codes exist exactly once at creation (in the row that created them), are
stored only as SHA-256 hashes, and are compared only in constant time.
No hash, no raw secret, and no password ever rides a payload past its
creation response, a log line, or an error detail.
"""

from collections.abc import Sequence
from typing import Annotated, Final, Literal, Protocol, runtime_checkable

from pydantic import Field

from guide.core.serialization import CamelModel

SESSION_COOKIE_NAME: Final = "fdg_session"
"""The login session's cookie name — the browser's half of the session id."""

SESSION_COOKIE_PATH: Final = "/api"
"""The cookie's path scope: the API tree only, never the whole origin."""

SESSION_MAX_AGE_SECONDS: Final = 900
"""The session cookie's Max-Age — 15 minutes, matched by the store row."""

SESSION_COOKIE_FLAGS: Final = ("HttpOnly", "SameSite=Lax")
"""The flags every session cookie carries; Secure is prod-only (dev is http)."""

API_KEY_PREFIX_BYTES: Final = 4
"""The readable prefix's entropy: 4 bytes → 8 hex chars, greppable not guessable."""

API_KEY_SECRET_BYTES: Final = 32
"""The secret half's entropy: 32 bytes → 256 bits, brute-force out of reach."""

KEY_NAME_MAX_LENGTH: Final = 60
"""The key record's display name cap — labels, not documents."""

CODE_TTL_SECONDS: Final = 600
"""An authorization code's life: ten minutes, one use."""

PKCE_VERIFIER_MIN: Final = 43
PKCE_VERIFIER_MAX: Final = 128
"""RFC 7636 §4.1: the verifier is 43–128 characters of unreserved ASCII."""

ACCESS_TOKEN_TTL_SECONDS: Final = 900
"""The demo access-token lifetime — 15 minutes, the standard short leash."""

REFRESH_TTL_SECONDS: Final = 3600 * 24
"""The refresh-token lifetime: one day per link, rotated at every use."""

Scopes = tuple[str, ...]
"""An immutable scope list — the vocabulary topics 23 and 24 share."""

TokenOutcome = Literal[
    "valid", "expired", "not-yet-valid", "bad-signature", "malformed"
]
"""How a token verification ended — every PyJWT failure mode, named."""

RefreshOutcome = Literal["rotated", "reuse-detected", "invalid"]
"""How a refresh exchange ended: rotated, reuse detected, or unknown token."""


# ── Identity rows ─────────────────────────────────────────────────────────────


class DemoUser(CamelModel):
    """One seeded user: identity, the password HASH, and the user's scopes.

    The raw password exists nowhere in the running app — only the argon2
    hash does, and it travels only into the password service.
    """

    username: str
    display_name: str
    password_hash: str
    scopes: Scopes


class StoredSession(CamelModel):
    """The server-side half of a login session.

    The cookie carries only the signed session id; everything else
    (who, when, what scopes) lives here, server-side.
    """

    session_id: str
    username: str
    display_name: str
    scopes: Scopes
    issued_at: str
    expires_at: str


class CookieInstruction(CamelModel):
    """What the router must put in Set-Cookie — the service's one output.

    ``max_age_seconds`` 0 with an empty value is the CLEAR instruction
    (logout); the flags mirror what the service promised to set.
    """

    name: str
    value: str
    max_age_seconds: int
    path: str
    httponly: bool
    samesite: Literal["lax", "strict", "none"]
    secure: bool


class StoredApiKey(CamelModel):
    """One API key record — the SHA-256 hash, never the key itself."""

    prefix: str
    name: str
    scopes: Scopes
    key_hash: str
    created_at: str


class StoredAuthorizationCode(CamelModel):
    """One issued authorization code: one-time, bound to client + URI + PKCE."""

    code_hash: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: Literal["S256"]
    username: str
    scopes: Scopes
    issued_at: str
    expires_at: str


class StoredRefreshFamily(CamelModel):
    """One refresh-token family: born at login, revoked as a unit on reuse."""

    family_id: str
    username: str
    status: Literal["active", "revoked"]
    created_at: str


class StoredRefreshToken(CamelModel):
    """One link in a refresh family — the hash, its state, its position.

    ``status``: active (never presented), used (rotated away — replaying
    it is THE reuse signal), revoked (family dead).
    """

    token_hash: str
    family_id: str
    position: int
    status: Literal["active", "used", "revoked"]
    issued_at: str
    used_at: str | None


# ── The ports ────────────────────────────────────────────────────────────────


@runtime_checkable
class UserDirectory(Protocol):
    """Resolve a username to its user row — the credential lookup."""

    async def find_user(self, username: str) -> DemoUser | None:
        """The user, or None when no such username exists."""
        ...

    async def list_users(self) -> list[DemoUser]:
        """Every user, oldest first — the credential roster the panel shows."""
        ...


@runtime_checkable
class SessionStore(Protocol):
    """Server-side session state: create, find, revoke, list."""

    async def create_session(self, session: StoredSession) -> None:
        """Record a new session (the login's server half)."""
        ...

    async def find_session(self, session_id: str) -> StoredSession | None:
        """The session, or None when unknown or expired."""
        ...

    async def revoke_session(self, session_id: str) -> bool:
        """Delete the session; True when a live session was revoked."""
        ...

    async def list_sessions(self) -> list[StoredSession]:
        """Every live session, oldest first — the panel's roster."""
        ...


@runtime_checkable
class ApiKeyStore(Protocol):
    """API key records keyed by prefix, hashed at rest."""

    async def save_key(self, record: StoredApiKey) -> None:
        """Store a new key record (hash only)."""
        ...

    async def find_key_by_prefix(self, prefix: str) -> StoredApiKey | None:
        """The record for this prefix, or None — the lookup half of verify."""
        ...

    async def revoke_key(self, prefix: str) -> bool:
        """Revoke by prefix; True when a record was removed."""
        ...

    async def list_keys(self) -> list[StoredApiKey]:
        """Every record, oldest first — the roster (hashes stay inside)."""
        ...


@runtime_checkable
class AuthorizationCodeStore(Protocol):
    """The authorization server's code shelf: issue once, take once."""

    async def issue_code(self, code: StoredAuthorizationCode) -> None:
        """Record a freshly issued code."""
        ...

    async def take_code(self, code_hash: str) -> StoredAuthorizationCode | None:
        """Consume the code — gone after this call, whatever follows."""
        ...


@runtime_checkable
class RefreshStore(Protocol):
    """Refresh families and their tokens, hashed at rest."""

    async def start_family(
        self, family: StoredRefreshFamily, token: StoredRefreshToken
    ) -> None:
        """Create the family and its first (active) token together."""
        ...

    async def find_token(self, token_hash: str) -> StoredRefreshToken | None:
        """The token record for this hash, whatever its status."""
        ...

    async def find_family(self, family_id: str) -> StoredRefreshFamily | None:
        """The family record, whatever its status."""
        ...

    async def add_token(self, token: StoredRefreshToken) -> None:
        """Append the next rotated link to its family."""
        ...

    async def mark_used(self, token_hash: str, used_at: str) -> None:
        """Flip an active token to used — the rotation's bookkeeping."""
        ...

    async def revoke_family(self, family_id: str) -> int:
        """Revoke the family and every token in it; count the tokens killed."""
        ...

    async def list_families(self) -> list[tuple[StoredRefreshFamily, list[StoredRefreshToken]]]:
        """Every family with its tokens, oldest family first."""
        ...


# ── Request bodies (routers parse; bounds are the contract) ──────────────────


class LoginRequest(CamelModel):
    """The login form's body: username + password, nothing else."""

    username: Annotated[str, Field(min_length=1, max_length=60)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class CreateKeyRequest(CamelModel):
    """The generate button's body: a display name and the key's scopes."""

    name: Annotated[str, Field(min_length=1, max_length=KEY_NAME_MAX_LENGTH)] = "demo key"
    scopes: Annotated[list[str], Field(min_length=1, max_length=8)] = ["posts:read"]


class RevokeKeyRequest(CamelModel):
    """The revoke button's body: which prefix to retire."""

    prefix: Annotated[str, Field(min_length=1, max_length=32)]


class MintTokenRequest(CamelModel):
    """The mint form's body: who, which scopes, how long, when it starts.

    ``sign_with`` "wrong" signs with a DIFFERENT secret on purpose — the
    lab's stand-in for an attacker-forged token, so the invalid-signature
    path is real and not hand-edited bytes.
    """

    username: Annotated[str, Field(min_length=1, max_length=60)] = "ada"
    scopes: Annotated[list[str], Field(min_length=0, max_length=8)] = ["posts:read"]
    ttl_seconds: Annotated[int, Field(default=ACCESS_TOKEN_TTL_SECONDS, ge=1, le=3600)] = (
        ACCESS_TOKEN_TTL_SECONDS
    )
    not_before_seconds: Annotated[int, Field(default=0, ge=0, le=3600)] = 0
    sign_with: Literal["real", "wrong"] = "real"


class VerifyTokenRequest(CamelModel):
    """The verify button's body: any token, any signature."""

    token: Annotated[str, Field(min_length=1, max_length=4096)]


class AuthorizeRequest(CamelModel):
    """The authorize step's body — exactly what a real client sends."""

    client_id: Annotated[str, Field(min_length=1, max_length=64)]
    redirect_uri: Annotated[str, Field(min_length=1, max_length=256)]
    state: Annotated[str, Field(max_length=256)] = ""
    code_challenge: Annotated[str, Field(min_length=PKCE_VERIFIER_MIN, max_length=128)]
    code_challenge_method: Literal["S256"] = "S256"


class TokenExchangeRequest(CamelModel):
    """The token endpoint's body: the one-time code plus the PKCE verifier."""

    code: Annotated[str, Field(min_length=1, max_length=128)]
    verifier: Annotated[str, Field(min_length=1, max_length=PKCE_VERIFIER_MAX)]
    redirect_uri: Annotated[str, Field(min_length=1, max_length=256)]


class HashPasswordRequest(CamelModel):
    """The hash button's body — the raw password exists here and nowhere else."""

    password: Annotated[str, Field(min_length=1, max_length=128)]


class VerifyPasswordRequest(CamelModel):
    """The verify button's body: a password and a hash to test it against."""

    password: Annotated[str, Field(min_length=1, max_length=128)]
    hash: Annotated[str, Field(min_length=1, max_length=512)]


class RefreshLoginRequest(LoginRequest):
    """The refresh lab's login: same credentials, family-scoped."""


class RefreshExchangeRequest(CamelModel):
    """The exchange button's body: one refresh token, raw, one time."""

    refresh_token: Annotated[str, Field(min_length=1, max_length=512)]


# ── Result rows ──────────────────────────────────────────────────────────────


class SessionLoginRow(CamelModel):
    """One login: the identity established and the cookie it set."""

    username: str
    display_name: str
    scopes: Scopes
    cookie: CookieInstruction
    cookie_value_anatomy: str
    detail: str


class SessionInspectionRow(CamelModel):
    """What /me answers for a live session — the session, explained."""

    session_id_preview: str
    username: str
    display_name: str
    scopes: Scopes
    issued_at: str
    expires_at: str
    detail: str


class SessionLogoutRow(CamelModel):
    """One logout: the server session revoked, the cookie cleared."""

    revoked: bool
    cookie: CookieInstruction
    detail: str


class ApiKeyCreatedRow(CamelModel):
    """One generated key — the ONLY response where the raw key appears."""

    prefix: str
    key: str
    key_hash: str
    name: str
    scopes: Scopes
    detail: str


class ApiKeyCallRow(CamelModel):
    """One authenticated call with an API key: who the key speaks for."""

    prefix: str
    name: str
    scopes: Scopes
    detail: str


class ApiKeyRevokeRow(CamelModel):
    """One revocation: the prefix retired, instantly dead."""

    prefix: str
    revoked: bool
    detail: str


class TokenLoginRow(CamelModel):
    """The OAuth2 login form's answer — the bearer-token response shape."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    username: str
    detail: str


class MintedTokenRow(CamelModel):
    """One minted token with its decoded anatomy — header and payload."""

    token: str
    header: dict[str, str]
    payload: dict[str, object]
    signed_with: Literal["real", "wrong"]
    expires_at: str
    detail: str


class TokenVerifyRow(CamelModel):
    """One verification's verdict — every failure mode named, no secrets."""

    outcome: TokenOutcome
    username: str | None
    scopes: Scopes | None
    expires_at: str | None
    detail: str


class BearerResourceRow(CamelModel):
    """What a protected resource answers: the caller the token establishes."""

    username: str
    scopes: Scopes
    via: str
    detail: str


class PkcePairRow(CamelModel):
    """A generated verifier/challenge pair — S256, ready to paste."""

    verifier: str
    code_challenge: str
    method: Literal["S256"]
    detail: str


class AuthorizeRow(CamelModel):
    """One authorize outcome: the redirect a real client would follow."""

    redirect_to: str
    state: str
    consent: str
    code_preview: str
    expires_in: int
    detail: str


class ExchangeRow(CamelModel):
    """One successful code exchange: the access token the client earned."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    username: str
    detail: str


class PasswordHashRow(CamelModel):
    """One hash round: the argon2 string, the params, the honest cost."""

    hash: str
    algorithm: str
    parameters: str
    elapsed_ms: int
    detail: str


class PasswordVerifyRow(CamelModel):
    """One verify round: match verdict, rehash verdict, honest timing."""

    ok: bool
    needs_rehash: bool
    elapsed_ms: int
    error: str | None
    detail: str


class RefreshLoginRow(CamelModel):
    """One family born: the access token, the refresh token (raw, once)."""

    family_id: str
    username: str
    access_token: str
    access_expires_in: int
    refresh_token: str
    detail: str


class RefreshExchangeRow(CamelModel):
    """One exchange outcome — rotated, reuse detected, or invalid."""

    outcome: RefreshOutcome
    family_id: str | None
    access_token: str | None
    access_expires_in: int | None
    refresh_token: str | None
    rotated_from_position: int | None
    family_tokens_revoked: int
    detail: str


ScopeList = Sequence[str]
"""Alias for scope sequences arriving at service boundaries."""
