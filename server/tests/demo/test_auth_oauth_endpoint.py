"""The OAuth lab endpoints — pkce pair, authorize, exchange, resource.

The full code+PKCE round over HTTP: the pair mints a real S256
verifier/challenge, authorize validates the registered client and its
exact redirect_uri and answers the redirect with a one-time code, the
exchange burns the code on FIRST presentation (a wrong verifier kills
it), and the protected resource accepts the exchanged Bearer token with
a scope check (403 when scopes do not carry posts:read — topic 24's
preview, real here).
"""

import pytest
from fastapi.testclient import TestClient

ROSTER_PATH = "/api/demo/auth/oauth"
PKCE_PATH = "/api/demo/auth/oauth/pkce"
AUTHORIZE_PATH = "/api/demo/auth/oauth/authorize"
TOKEN_PATH = "/api/demo/auth/oauth/token"
PROTECTED_PATH = "/api/demo/auth/oauth/protected"

REDIRECT_URI = "https://client.example/callback"


def _pair(client: TestClient) -> dict[str, str]:
    return client.post(PKCE_PATH).json()


def _authorize(client: TestClient, challenge: str) -> str:
    response = client.post(
        AUTHORIZE_PATH,
        json={
            "clientId": "guide-cli",
            "redirectUri": REDIRECT_URI,
            "state": "tour",
            "codeChallenge": challenge,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "tour"
    assert body["redirectTo"].startswith(f"{REDIRECT_URI}?code=")
    assert "consent" in body["consent"].lower()
    return body["redirectTo"].split("code=")[1].split("&")[0]


def test_panel_maps_the_flow(client: TestClient) -> None:
    body = client.get(ROSTER_PATH).json()
    assert body["clientId"] == "guide-cli"
    assert body["redirectUris"] == [REDIRECT_URI]
    assert body["clientScopes"] == ["posts:read", "posts:write"]
    assert len(body["steps"]) == 4
    assert body["codeTtlSeconds"] == 600


def test_pkce_pair_is_s256_shaped(client: TestClient) -> None:
    pair = _pair(client)
    assert len(pair["verifier"]) >= 43
    assert pair["method"] == "S256"
    assert len(pair["codeChallenge"]) == 43  # base64url of a SHA-256, unpadded


def test_the_full_round_exchanges_and_unlocks_the_resource(client: TestClient) -> None:
    pair = _pair(client)
    code = _authorize(client, pair["codeChallenge"])
    exchange = client.post(
        TOKEN_PATH,
        json={"code": code, "verifier": pair["verifier"], "redirectUri": REDIRECT_URI},
    )
    assert exchange.status_code == 200
    granted = exchange.json()
    assert granted["tokenType"] == "Bearer"
    assert granted["scope"] == "posts:read posts:write"

    resource = client.get(
        PROTECTED_PATH, headers={"Authorization": f"Bearer {granted['accessToken']}"}
    )
    assert resource.status_code == 200
    assert resource.json()["username"] == "ada"


def test_wrong_verifier_rejects_and_burns_the_code(client: TestClient) -> None:
    pair = _pair(client)
    code = _authorize(client, pair["codeChallenge"])
    wrong = client.post(
        TOKEN_PATH,
        json={"code": code, "verifier": "y" * 43, "redirectUri": REDIRECT_URI},
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "unauthorized"

    retry = client.post(
        TOKEN_PATH,
        json={"code": code, "verifier": pair["verifier"], "redirectUri": REDIRECT_URI},
    )
    assert retry.status_code == 401  # one attempt: the code is spent


def test_exchange_refusals_name_the_grant_error(client: TestClient) -> None:
    pair = _pair(client)
    unknown = client.post(
        TOKEN_PATH,
        json={"code": "never-issued", "verifier": pair["verifier"], "redirectUri": REDIRECT_URI},
    )
    assert unknown.status_code == 401
    assert "invalid_grant" in unknown.json()["error"]["message"]

    code = _authorize(client, pair["codeChallenge"])
    mismatched = client.post(
        TOKEN_PATH,
        json={
            "code": code,
            "verifier": pair["verifier"],
            "redirectUri": "https://attacker.example/callback",
        },
    )
    assert mismatched.status_code == 401
    assert "redirect_uri" in mismatched.json()["error"]["message"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"clientId": "evil-app"},
        {"redirectUri": "https://attacker.example/callback"},
        {"codeChallenge": "too-short"},
    ],
)
def test_authorize_refuses_bad_registrations(client: TestClient, overrides: dict[str, str]) -> None:
    pair = _pair(client)
    request = {
        "clientId": "guide-cli",
        "redirectUri": REDIRECT_URI,
        "state": "s",
        "codeChallenge": pair["codeChallenge"],
    } | overrides
    response = client.post(AUTHORIZE_PATH, json=request)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_resource_requires_the_scope_not_just_a_token(client: TestClient) -> None:
    minted = client.post(
        "/api/demo/auth/jwt/mint", json={"username": "ada", "scopes": []}
    ).json()
    response = client.get(
        PROTECTED_PATH, headers={"Authorization": f"Bearer {minted['token']}"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert "posts:read" in response.json()["error"]["message"]
