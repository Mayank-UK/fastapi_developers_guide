"""The JWT demo payload: the token anatomy, derived purely.

``GET /api/demo/auth/jwt`` serves this payload — topic 23's fourth demo
(``auth:jwt``), inline in the JWT section. The panel carries the token's
contract (algorithm, issuer, the claim set minted, the standard
lifetime) and the login-form endpoint the OAuth2 password flow uses.
"""

from guide.core.serialization import CamelModel

CLAIM_ANATOMY: tuple[tuple[str, str], ...] = (
    ("sub", "the subject — WHO the token speaks for (the username)"),
    ("iat", "issued-at — when minting happened, seconds since epoch"),
    ("exp", "expiry — the hard lease; past this instant the token is refuse"),
    ("nbf", "not-before — validity's start gate; earlier presentations are premature"),
    ("iss", "issuer — who signed; the verifier demands its own value here"),
    ("scopes", "the authority carried — what the token permits, checked per route"),
    ("jti", "a unique id — the handle for audit trails and future deny-lists"),
)
"""The claim set the mint builds — the panel and the prose share it."""


class ClaimRow(CamelModel):
    """One claim of the anatomy table: name and what it asserts."""

    claim: str
    meaning: str


class JwtPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/auth/jwt`` — the token lab's contract."""

    algorithm: str
    issuer: str
    default_ttl_seconds: int
    claims: list[ClaimRow]
    login_endpoint: str
    mint_endpoint: str
    verify_endpoint: str
    protected_endpoint: str
    reasoning: str


def build_jwt_panel_payload(
    *,
    algorithm: str,
    issuer: str,
    default_ttl_seconds: int,
    login_endpoint: str,
    mint_endpoint: str,
    verify_endpoint: str,
    protected_endpoint: str,
) -> JwtPanelPayload:
    """Shape the anatomy (pure) — the contract every minted token carries."""
    reasoning = (
        f"One HS256 secret signs and verifies; the token is three base64url parts "
        f"joined by dots — header ({{alg: {algorithm}}}), the claim set above, and a "
        "signature over both. Verification consults NOTHING but the signature and "
        f"the claims: no store, no session — stateless, revocation-approximate "
        f"(expiry, {default_ttl_seconds}s by default, is the only lever), which is "
        "exactly the trade the refresh-rotation section repairs. The login "
        "endpoint is the OAuth2 password form flow FastAPI documents natively: "
        "username/password in, bearer token out."
    )
    return JwtPanelPayload(
        algorithm=algorithm,
        issuer=issuer,
        default_ttl_seconds=default_ttl_seconds,
        claims=[ClaimRow(claim=claim, meaning=meaning) for claim, meaning in CLAIM_ANATOMY],
        login_endpoint=login_endpoint,
        mint_endpoint=mint_endpoint,
        verify_endpoint=verify_endpoint,
        protected_endpoint=protected_endpoint,
        reasoning=reasoning,
    )
