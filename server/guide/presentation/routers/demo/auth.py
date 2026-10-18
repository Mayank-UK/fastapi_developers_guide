"""Authentication demos: topic 23's six labs (area ``auth``).

Thin routers (family invariant). The cookie lab (``GET /sessions`` roster;
``POST /sessions/login`` verify → Set-Cookie with HttpOnly/SameSite=Lax;
``GET /sessions/me`` the authenticated inspection or the 401 envelope;
``POST /sessions/logout`` store deletion + cookie clear) runs over the
``SessionService``. The key lab (``GET /keys`` roster by prefix;
``POST /keys`` generate — the raw key shown once; ``POST /keys/call``
the protected endpoint authenticating the ``x-api-key`` header, 401 on
any failure; ``POST /keys/revoke`` instant death) runs over
``ApiKeyService``. The token lab (``GET /jwt`` the anatomy; ``POST
/jwt/login`` the OAuth2 password FORM flow; ``POST /jwt/mint`` claims on
demand — including the wrong-secret forgery option; ``POST /jwt/verify``
every failure classified; ``GET /jwt/protected`` the Bearer guard) runs
over ``TokenService``. The OAuth lab (``GET /oauth`` the map; ``POST
/oauth/pkce`` the pair; ``POST /oauth/authorize`` consent + one-time
code; ``POST /oauth/token`` the PKCE exchange — a wrong verifier is a
dead code and a 401; ``GET /oauth/protected`` the resource with a scope
check) runs over ``OAuthProviderService``. The hashing lab (``GET
/hashing`` the contract; ``POST /hashing/hash`` real cost; ``POST
/hashing/verify`` match + rehash signal) runs over ``PasswordService``.
The refresh lab (``GET /refresh`` the family board; ``POST
/refresh/login`` family birth; ``POST /refresh/exchange`` rotate, or
detect reuse and revoke the family) runs over ``RefreshRotationService``.
Everything is in-memory per app — no external store, no 503 paths here.
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from guide.core.errors import AppError, FailureKind
from guide.domain.auth.api_key_service import NEVER_STORE_RAW_NOTE as KEYS_STORAGE_NOTE
from guide.domain.auth.api_key_service import ApiKeyService
from guide.domain.auth.jwt_service import (
    STATELESS_NOTE,
    TOKEN_ALGORITHM,
    TOKEN_ISSUER,
    TokenService,
)
from guide.domain.auth.oauth_service import (
    CLIENT_ID,
    CLIENT_NAME,
    CLIENT_SCOPES,
    PKCE_NOTE,
    REGISTERED_REDIRECT_URIS,
    OAuthProviderService,
)
from guide.domain.auth.password_service import (
    HASHING_VS_ENCRYPTION_NOTE,
    LEGACY_PARAMETERS,
    PasswordService,
)
from guide.domain.auth.ports import (
    ACCESS_TOKEN_TTL_SECONDS,
    SESSION_COOKIE_FLAGS,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_PATH,
    SESSION_MAX_AGE_SECONDS,
    ApiKeyCallRow,
    ApiKeyCreatedRow,
    ApiKeyRevokeRow,
    AuthorizeRequest,
    AuthorizeRow,
    BearerResourceRow,
    CookieInstruction,
    CreateKeyRequest,
    ExchangeRow,
    HashPasswordRequest,
    LoginRequest,
    MintedTokenRow,
    MintTokenRequest,
    PasswordHashRow,
    PasswordVerifyRow,
    PkcePairRow,
    RefreshExchangeRequest,
    RefreshExchangeRow,
    RefreshLoginRequest,
    RefreshLoginRow,
    RevokeKeyRequest,
    SessionInspectionRow,
    SessionLoginRow,
    SessionLogoutRow,
    SessionStore,
    TokenExchangeRequest,
    TokenLoginRow,
    TokenVerifyRow,
    UserDirectory,
    VerifyPasswordRequest,
    VerifyTokenRequest,
)
from guide.domain.auth.ports import (
    CODE_TTL_SECONDS as OAUTH_CODE_TTL_SECONDS,
)
from guide.domain.auth.refresh_service import REUSE_NOTE, RefreshRotationService
from guide.domain.auth.session_service import SIGNED_COOKIE_NOTE, SessionService
from guide.domain.demos.auth_api_keys import ApiKeysPanelPayload, build_api_keys_panel_payload
from guide.domain.demos.auth_hashing import HashingPanelPayload, build_hashing_panel_payload
from guide.domain.demos.auth_jwt import JwtPanelPayload, build_jwt_panel_payload
from guide.domain.demos.auth_oauth import OAuthPanelPayload, build_oauth_panel_payload
from guide.domain.demos.auth_refresh import RefreshPanelPayload, build_refresh_panel_payload
from guide.domain.demos.auth_sessions import SessionsPanelPayload, build_sessions_panel_payload

router = APIRouter(prefix="/api/demo/auth", tags=["demo:auth"])

SESSIONS_PATH: Final = "/sessions"
SESSIONS_LOGIN_PATH: Final = "/sessions/login"
SESSIONS_ME_PATH: Final = "/sessions/me"
SESSIONS_LOGOUT_PATH: Final = "/sessions/logout"
KEYS_PATH: Final = "/keys"
KEYS_CALL_PATH: Final = "/keys/call"
KEYS_REVOKE_PATH: Final = "/keys/revoke"
JWT_PATH: Final = "/jwt"
JWT_LOGIN_PATH: Final = "/jwt/login"
JWT_MINT_PATH: Final = "/jwt/mint"
JWT_VERIFY_PATH: Final = "/jwt/verify"
JWT_PROTECTED_PATH: Final = "/jwt/protected"
OAUTH_PATH: Final = "/oauth"
OAUTH_PKCE_PATH: Final = "/oauth/pkce"
OAUTH_AUTHORIZE_PATH: Final = "/oauth/authorize"
OAUTH_TOKEN_PATH: Final = "/oauth/token"
OAUTH_PROTECTED_PATH: Final = "/oauth/protected"
HASHING_PATH: Final = "/hashing"
HASHING_HASH_PATH: Final = "/hashing/hash"
HASHING_VERIFY_PATH: Final = "/hashing/verify"
REFRESH_PATH: Final = "/refresh"
REFRESH_LOGIN_PATH: Final = "/refresh/login"
REFRESH_EXCHANGE_PATH: Final = "/refresh/exchange"
"""The six labs' paths — the terminal companion's tour names them."""

KEYS_LOOKUP_NOTE: Final = (
    "lookup is prefix-keyed and the hash comparison is constant-time — "
    "hmac.compare_digest over two SHA-256 hex digests, no early exit to time"
)
"""The lookup rule, shown on the keys panel."""

PASSWORDS_LOGGING_NOTE: Final = (
    "timings and verdicts may appear in logs and responses; passwords, keys, and "
    "tokens never do — a log line carries the outcome, never the secret"
)
"""The logging rule, shown on the hashing panel."""

PROTECTED_SCOPE: Final = "posts:read"
"""The scope both protected resources demand — the topic-24 preview."""

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{router.prefix}{JWT_LOGIN_PATH}", auto_error=False
)
"""The Bearer guard FastAPI documents natively. ``auto_error=False`` keeps
this guide's ONE error envelope in charge of the 401 (FastAPI's built-in
error raises a bare detail shape) and lets the token service classify the
failure itself — missing, expired, forged: one envelope, named causes."""


def _wired[Wired](service: object, expected: type[Wired], name: str) -> Wired:
    """The one wiring check every auth dependency shares."""
    if not isinstance(service, expected):
        raise AppError(FailureKind.INTERNAL, f"{name} not wired on app.state")
    return service


def get_session_service(request: Request) -> SessionService:
    """FastAPI dependency: the cookie-lab engine (wired in create_app)."""
    return _wired(request.app.state.auth_sessions, SessionService, "Session service")


def get_api_key_service(request: Request) -> ApiKeyService:
    return _wired(request.app.state.auth_api_keys, ApiKeyService, "API key service")


def get_token_service(request: Request) -> TokenService:
    return _wired(request.app.state.auth_tokens, TokenService, "Token service")


def get_oauth_provider(request: Request) -> OAuthProviderService:
    return _wired(request.app.state.auth_oauth, OAuthProviderService, "OAuth provider")


def get_refresh_service(request: Request) -> RefreshRotationService:
    return _wired(request.app.state.auth_refresh, RefreshRotationService, "Refresh service")


def get_password_service(request: Request) -> PasswordService:
    return _wired(request.app.state.auth_passwords, PasswordService, "Password service")


def get_session_store(request: Request) -> SessionStore:
    """FastAPI dependency: the auth state behind the session port.

    The check is inline (not ``_wired``) because a Protocol class cannot
    ride a ``type[T]`` parameter — runtime_checkable isinstance is the
    one shape mypy accepts for ports.
    """
    store = request.app.state.auth_state
    if not isinstance(store, SessionStore):
        raise AppError(FailureKind.INTERNAL, "Auth state store not wired on app.state")
    return store


def get_user_directory(request: Request) -> UserDirectory:
    """FastAPI dependency: the seeded user directory (same adapter)."""
    directory = request.app.state.auth_state
    if not isinstance(directory, UserDirectory):
        raise AppError(FailureKind.INTERNAL, "User directory not wired on app.state")
    return directory


SessionDep = Annotated[SessionService, Depends(get_session_service)]
ApiKeyDep = Annotated[ApiKeyService, Depends(get_api_key_service)]
TokenDep = Annotated[TokenService, Depends(get_token_service)]
OAuthDep = Annotated[OAuthProviderService, Depends(get_oauth_provider)]
RefreshDep = Annotated[RefreshRotationService, Depends(get_refresh_service)]
PasswordDep = Annotated[PasswordService, Depends(get_password_service)]
SessionStoreDep = Annotated[SessionStore, Depends(get_session_store)]
DirectoryDep = Annotated[UserDirectory, Depends(get_user_directory)]
BearerToken = Annotated[str | None, Depends(oauth2_scheme)]


def _apply_cookie(response: Response, cookie: CookieInstruction) -> None:
    """Apply the service's cookie instruction verbatim — flags are its call."""
    response.set_cookie(
        key=cookie.name,
        value=cookie.value,
        max_age=cookie.max_age_seconds,
        path=cookie.path,
        httponly=cookie.httponly,
        samesite=cookie.samesite,
        secure=cookie.secure,
    )


# ── The cookie lab (auth:sessions) ───────────────────────────────────────────


@router.get(SESSIONS_PATH, response_model=SessionsPanelPayload)
async def read_sessions_panel(store: SessionStoreDep) -> SessionsPanelPayload:
    """The cookie lab roster: the contract + every live session."""
    sessions = await store.list_sessions()
    return build_sessions_panel_payload(
        sessions,
        cookie_name=SESSION_COOKIE_NAME,
        cookie_path=SESSION_COOKIE_PATH,
        max_age_seconds=SESSION_MAX_AGE_SECONDS,
        flags_set=list(SESSION_COOKIE_FLAGS),
        seal_note=SIGNED_COOKIE_NOTE,
        login_endpoint=f"{router.prefix}{SESSIONS_LOGIN_PATH}",
        me_endpoint=f"{router.prefix}{SESSIONS_ME_PATH}",
        logout_endpoint=f"{router.prefix}{SESSIONS_LOGOUT_PATH}",
    )


@router.post(SESSIONS_LOGIN_PATH, response_model=SessionLoginRow)
async def login_session(
    service: SessionDep, request: LoginRequest, response: Response
) -> SessionLoginRow:
    """The login button: verify → session → Set-Cookie with real flags."""
    row = await service.login(request)
    _apply_cookie(response, row.cookie)
    return row


@router.get(SESSIONS_ME_PATH, response_model=SessionInspectionRow)
async def inspect_session(service: SessionDep, request: Request) -> SessionInspectionRow:
    """The authenticated call: the cookie resolves to a live session or 401."""
    return await service.inspect(request.cookies.get(SESSION_COOKIE_NAME))


@router.post(SESSIONS_LOGOUT_PATH, response_model=SessionLogoutRow)
async def logout_session(
    service: SessionDep, request: Request, response: Response
) -> SessionLogoutRow:
    """The logout button: delete the server session, expire the cookie."""
    row = await service.logout(request.cookies.get(SESSION_COOKIE_NAME))
    _apply_cookie(response, row.cookie)
    return row


# ── The key lab (auth:api-keys) ──────────────────────────────────────────────


@router.get(KEYS_PATH, response_model=ApiKeysPanelPayload)
async def read_keys_panel(service: ApiKeyDep) -> ApiKeysPanelPayload:
    """The key roster: prefixes and hash previews, never secrets."""
    records = await service.roster()
    return build_api_keys_panel_payload(
        records,
        storage_note=KEYS_STORAGE_NOTE,
        lookup_note=KEYS_LOOKUP_NOTE,
        create_endpoint=f"{router.prefix}{KEYS_PATH}",
        call_endpoint=f"{router.prefix}{KEYS_CALL_PATH}",
        revoke_endpoint=f"{router.prefix}{KEYS_REVOKE_PATH}",
    )


@router.post(KEYS_PATH, response_model=ApiKeyCreatedRow)
async def generate_key(service: ApiKeyDep, request: CreateKeyRequest) -> ApiKeyCreatedRow:
    """The generate button: mint prefix + secret — the raw key's only appearance."""
    return await service.generate(request)


@router.post(KEYS_CALL_PATH, response_model=ApiKeyCallRow)
async def call_with_key(
    service: ApiKeyDep,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> ApiKeyCallRow:
    """The protected call: the x-api-key header authenticates or 401s."""
    return await service.call(x_api_key)


@router.post(KEYS_REVOKE_PATH, response_model=ApiKeyRevokeRow)
async def revoke_key(service: ApiKeyDep, request: RevokeKeyRequest) -> ApiKeyRevokeRow:
    """The revoke button: prefix-keyed delete, instantly dead."""
    return await service.revoke(request.prefix)


# ── The token lab (auth:jwt) ─────────────────────────────────────────────────


@router.get(JWT_PATH, response_model=JwtPanelPayload)
async def read_jwt_panel() -> JwtPanelPayload:
    """The token anatomy: algorithm, issuer, the claim set, the endpoints."""
    return build_jwt_panel_payload(
        algorithm=TOKEN_ALGORITHM,
        issuer=TOKEN_ISSUER,
        default_ttl_seconds=ACCESS_TOKEN_TTL_SECONDS,
        login_endpoint=f"{router.prefix}{JWT_LOGIN_PATH}",
        mint_endpoint=f"{router.prefix}{JWT_MINT_PATH}",
        verify_endpoint=f"{router.prefix}{JWT_VERIFY_PATH}",
        protected_endpoint=f"{router.prefix}{JWT_PROTECTED_PATH}",
    )


@router.post(JWT_LOGIN_PATH, response_model=TokenLoginRow)
async def login_token(
    service: TokenDep, form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> TokenLoginRow:
    """The OAuth2 password flow: form-encoded credentials in, bearer out."""
    return await service.login(form.username, form.password)


@router.post(JWT_MINT_PATH, response_model=MintedTokenRow)
async def mint_token(service: TokenDep, request: MintTokenRequest) -> MintedTokenRow:
    """The mint form: choose scopes, ttl, not-before — or the wrong secret."""
    return service.mint(request)


@router.post(JWT_VERIFY_PATH, response_model=TokenVerifyRow)
async def verify_token(service: TokenDep, request: VerifyTokenRequest) -> TokenVerifyRow:
    """The verify button: every failure mode classified, never a secret."""
    return service.verify(request.token)


@router.get(JWT_PROTECTED_PATH, response_model=BearerResourceRow)
async def protected_by_token(service: TokenDep, token: BearerToken) -> BearerResourceRow:
    """The guarded resource: Bearer in, caller + scopes out — or the 401."""
    username, scopes = service.require(token)
    return BearerResourceRow(
        username=username,
        scopes=scopes,
        via="Authorization: Bearer — verified statelessly against the signature",
        detail=STATELESS_NOTE,
    )


# ── The OAuth lab (auth:oauth) ───────────────────────────────────────────────


@router.get(OAUTH_PATH, response_model=OAuthPanelPayload)
async def read_oauth_panel() -> OAuthPanelPayload:
    """The flow's map: the registered client and the four steps."""
    return build_oauth_panel_payload(
        client_id=CLIENT_ID,
        client_kind=CLIENT_NAME,
        redirect_uris=list(REGISTERED_REDIRECT_URIS),
        client_scopes=list(CLIENT_SCOPES),
        code_ttl_seconds=OAUTH_CODE_TTL_SECONDS,
        pkce_note=PKCE_NOTE,
        pkce_endpoint=f"{router.prefix}{OAUTH_PKCE_PATH}",
        authorize_endpoint=f"{router.prefix}{OAUTH_AUTHORIZE_PATH}",
        token_endpoint=f"{router.prefix}{OAUTH_TOKEN_PATH}",
        protected_endpoint=f"{router.prefix}{OAUTH_PROTECTED_PATH}",
    )


@router.post(OAUTH_PKCE_PATH, response_model=PkcePairRow)
async def generate_pkce_pair(service: OAuthDep) -> PkcePairRow:
    """The pair button: verifier + S256 challenge, as a client would mint."""
    return service.pkce_pair()


@router.post(OAUTH_AUTHORIZE_PATH, response_model=AuthorizeRow)
async def authorize(service: OAuthDep, request: AuthorizeRequest) -> AuthorizeRow:
    """The authorize step: validate, consent, issue the one-time code."""
    return await service.authorize(request)


@router.post(OAUTH_TOKEN_PATH, response_model=ExchangeRow)
async def exchange_code(service: OAuthDep, request: TokenExchangeRequest) -> ExchangeRow:
    """The exchange step: code + verifier → token; wrong verifier kills the code."""
    return await service.exchange(request)


@router.get(OAUTH_PROTECTED_PATH, response_model=BearerResourceRow)
async def protected_by_oauth(
    service: TokenDep, token: BearerToken
) -> BearerResourceRow:
    """The resource the exchanged token unlocks — with the scope check."""
    username, scopes = service.require(token)
    if PROTECTED_SCOPE not in scopes:
        raise AppError(
            FailureKind.FORBIDDEN,
            f"token lacks the required scope {PROTECTED_SCOPE!r} — authentication "
            "said who you are; authorization (topic 24) says what that allows",
        )
    return BearerResourceRow(
        username=username,
        scopes=scopes,
        via="the OAuth code+PKCE exchange's Bearer token",
        detail=(
            f"the access token earned through authorize → exchange carries "
            f"{PROTECTED_SCOPE} among its scopes, and this check is the whole "
            "difference between authentication (who) and authorization (what) — "
            "topic 24 builds the general machinery"
        ),
    )


# ── The hashing lab (auth:hashing) ───────────────────────────────────────────


@router.get(HASHING_PATH, response_model=HashingPanelPayload)
async def read_hashing_panel(
    passwords: PasswordDep, directory: DirectoryDep
) -> HashingPanelPayload:
    """The hashing contract: cost, legacy cost, the seeded credentials."""
    users = await directory.list_users()
    return build_hashing_panel_payload(
        users,
        algorithm="argon2id",
        parameters=passwords.parameters,
        legacy_parameters=LEGACY_PARAMETERS,
        distinction_note=HASHING_VS_ENCRYPTION_NOTE,
        logging_note=PASSWORDS_LOGGING_NOTE,
        hash_endpoint=f"{router.prefix}{HASHING_HASH_PATH}",
        verify_endpoint=f"{router.prefix}{HASHING_VERIFY_PATH}",
    )


@router.post(HASHING_HASH_PATH, response_model=PasswordHashRow)
async def hash_password(
    passwords: PasswordDep, request: HashPasswordRequest
) -> PasswordHashRow:
    """The hash button: fresh salt, stamped parameters, honest milliseconds."""
    return passwords.hash_password(request)


@router.post(HASHING_VERIFY_PATH, response_model=PasswordVerifyRow)
async def verify_password(
    passwords: PasswordDep, request: VerifyPasswordRequest
) -> PasswordVerifyRow:
    """The verify button: match verdict, rehash verdict, same cost either way."""
    return passwords.verify_password(request)


# ── The refresh lab (auth:refresh) ───────────────────────────────────────────


@router.get(REFRESH_PATH, response_model=RefreshPanelPayload)
async def read_refresh_panel(service: RefreshDep) -> RefreshPanelPayload:
    """The family board: every family's token timeline + the counters."""
    families = await service.families()
    return build_refresh_panel_payload(
        families,
        logins=service.logins,
        rotations=service.rotations,
        reuse_events=service.reuse_events,
        pattern_note=REUSE_NOTE,
        login_endpoint=f"{router.prefix}{REFRESH_LOGIN_PATH}",
        exchange_endpoint=f"{router.prefix}{REFRESH_EXCHANGE_PATH}",
    )


@router.post(REFRESH_LOGIN_PATH, response_model=RefreshLoginRow)
async def login_refresh(
    service: RefreshDep, request: RefreshLoginRequest
) -> RefreshLoginRow:
    """The login button: family birth — first refresh token, raw once."""
    return await service.login(request)


@router.post(REFRESH_EXCHANGE_PATH, response_model=RefreshExchangeRow)
async def exchange_refresh(
    service: RefreshDep, request: RefreshExchangeRequest
) -> RefreshExchangeRow:
    """The exchange button: rotate to the next link — or trip the reuse alarm."""
    return await service.exchange(request)
