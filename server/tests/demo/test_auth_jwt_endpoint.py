"""The token lab endpoints — form login, mint dials, verify verdicts, guard.

The OAuth2 password FORM flow (urlencoded body) answers a bearer token;
the mint dials build every claim shape including the wrong-secret
forgery; verify classifies each failure mode; the protected endpoint
turns every non-valid outcome into the one 401 envelope. The EXPIRED
path is deterministic: the token is minted through the SAME engine with
an explicit past clock (the test constructs the engine pair the app
wires), so no sleep is ever needed.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from guide.data.auth import InMemoryAuthState
from guide.domain.auth.jwt_service import TokenService
from guide.domain.auth.password_service import PasswordService, production_hasher
from guide.domain.auth.ports import MintTokenRequest

ROSTER_PATH = "/api/demo/auth/jwt"
LOGIN_PATH = "/api/demo/auth/jwt/login"
MINT_PATH = "/api/demo/auth/jwt/mint"
VERIFY_PATH = "/api/demo/auth/jwt/verify"
PROTECTED_PATH = "/api/demo/auth/jwt/protected"


def _expired_token() -> str:
    """Mint through the real engine with a past clock — deterministic expiry."""
    state = InMemoryAuthState()
    engine = TokenService(
        "dev-only-jwt-secret-override-me-32+chars", state, PasswordService(production_hasher())
    )
    minted = engine.mint(
        MintTokenRequest(username="ada"),
        now=datetime.now(UTC) - timedelta(seconds=3600),
    )
    return minted.token


def test_panel_serves_the_anatomy(client: TestClient) -> None:
    body = client.get(ROSTER_PATH).json()
    assert body["algorithm"] == "HS256"
    assert body["issuer"] == "guide.demo"
    assert body["defaultTtlSeconds"] == 900
    claims = {row["claim"]: row["meaning"] for row in body["claims"]}
    assert set(claims) == {"sub", "iat", "exp", "nbf", "iss", "scopes", "jti"}
    assert body["loginEndpoint"] == LOGIN_PATH


def test_login_form_flow_answers_a_bearer_token(client: TestClient) -> None:
    response = client.post(LOGIN_PATH, data={"username": "grace", "password": "nanosecond"})
    assert response.status_code == 200
    body = response.json()
    assert body["tokenType"] == "bearer"
    assert body["scope"] == "posts:read"
    assert body["username"] == "grace"

    protected = client.get(
        PROTECTED_PATH, headers={"Authorization": f"Bearer {body['accessToken']}"}
    )
    assert protected.status_code == 200
    assert protected.json()["username"] == "grace"


def test_login_form_rejects_bad_credentials(client: TestClient) -> None:
    for payload in (
        {"username": "grace", "password": "wrong"},
        {"username": "ghost", "password": "nanosecond"},
    ):
        response = client.post(LOGIN_PATH, data=payload)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


def test_mint_dials_and_verify_classify_every_failure(client: TestClient) -> None:
    minted = client.post(MINT_PATH, json={"username": "ada", "scopes": ["posts:read"]}).json()
    assert minted["signedWith"] == "real"
    assert minted["payload"]["sub"] == "ada"
    assert client.post(VERIFY_PATH, json={"token": minted["token"]}).json()["outcome"] == "valid"

    forged = client.post(MINT_PATH, json={"username": "ada", "signWith": "wrong"}).json()
    assert forged["signedWith"] == "wrong"
    assert client.post(VERIFY_PATH, json={"token": forged["token"]}).json()["outcome"] == (
        "bad-signature"
    )

    premature = client.post(MINT_PATH, json={"notBeforeSeconds": 3600}).json()
    assert client.post(VERIFY_PATH, json={"token": premature["token"]}).json()["outcome"] == (
        "not-yet-valid"
    )

    assert client.post(VERIFY_PATH, json={"token": _expired_token()}).json()["outcome"] == (
        "expired"
    )
    assert client.post(VERIFY_PATH, json={"token": "garbage.not-a.jwt"}).json()["outcome"] == (
        "malformed"
    )


def test_protected_endpoint_guards_every_non_valid_outcome(client: TestClient) -> None:
    no_token = client.get(PROTECTED_PATH)
    assert no_token.status_code == 401
    assert no_token.json()["error"]["code"] == "unauthorized"

    forged = client.post(MINT_PATH, json={"signWith": "wrong"}).json()["token"]
    rejected = client.get(PROTECTED_PATH, headers={"Authorization": f"Bearer {forged}"})
    assert rejected.status_code == 401
    assert "bad-signature" in rejected.json()["error"]["message"]

    malformed = client.get(PROTECTED_PATH, headers={"Authorization": "Bearer nope"})
    assert malformed.status_code == 401


def test_mint_bounds_are_enforced(client: TestClient) -> None:
    assert client.post(MINT_PATH, json={"ttlSeconds": 0}).status_code == 422
    assert client.post(MINT_PATH, json={"ttlSeconds": 3601}).status_code == 422
    assert client.post(MINT_PATH, json={"notBeforeSeconds": -1}).status_code == 422
