"""The cookie lab endpoints — login, /me, logout, over the per-app store.

The Set-Cookie flags are asserted from the WIRE (the header the browser
would receive), the tampered-cookie and missing-cookie paths answer the
standard 401 envelope, and logout's invalidation is proven by replaying
the pre-logout cookie value after logout. The per-test app gives each
case a fresh in-memory auth world — no janitors needed.
"""

import pytest
from fastapi.testclient import TestClient

ROSTER_PATH = "/api/demo/auth/sessions"
LOGIN_PATH = "/api/demo/auth/sessions/login"
ME_PATH = "/api/demo/auth/sessions/me"
LOGOUT_PATH = "/api/demo/auth/sessions/logout"

ADA = {"username": "ada", "password": "analytical-engine"}


def test_roster_serves_the_cookie_contract(client: TestClient) -> None:
    body = client.get(ROSTER_PATH).json()
    assert body["cookieName"] == "fdg_session"
    assert body["cookiePath"] == "/api"
    assert body["maxAgeSeconds"] == 900
    assert body["flagsSet"] == ["HttpOnly", "SameSite=Lax"]
    assert "Secure" in body["secureNote"]
    assert body["activeSessions"] == []
    assert body["loginEndpoint"] == LOGIN_PATH


def test_login_sets_the_real_cookie_flags(client: TestClient) -> None:
    response = client.post(LOGIN_PATH, json=ADA)
    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == "Ada Lovelace"
    assert set(body["scopes"]) == {"posts:read", "posts:write"}
    cookie_header = response.headers["set-cookie"]
    assert "fdg_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert "Path=/api" in cookie_header
    assert "Max-Age=900" in cookie_header
    roster = client.get(ROSTER_PATH).json()
    assert len(roster["activeSessions"]) == 1
    assert roster["activeSessions"][0]["username"] == "ada"


def test_me_round_trip_and_logout_invalidation(client: TestClient) -> None:
    client.post(LOGIN_PATH, json=ADA)
    me = client.get(ME_PATH).json()
    assert me["username"] == "ada"
    assert me["sessionIdPreview"].endswith("…")
    assert me["expiresAt"] > me["issuedAt"]

    cookie_value = client.cookies.get("fdg_session")
    assert cookie_value is not None
    logout = client.post(LOGOUT_PATH)
    assert logout.json()["revoked"] is True
    assert "Max-Age=0" in logout.headers["set-cookie"]
    # Replay the PRE-logout cookie value: the store row is gone, so dead.
    dead = client.get(ME_PATH, cookies={"fdg_session": cookie_value})
    assert dead.status_code == 401
    assert dead.json()["error"]["code"] == "unauthorized"
    assert client.get(ROSTER_PATH).json()["activeSessions"] == []


def test_tampered_and_missing_cookies_answer_the_401_envelope(client: TestClient) -> None:
    client.post(LOGIN_PATH, json=ADA)
    good = client.cookies.get("fdg_session") or ""
    for bad in (good[:-2] + "xx", good.split(".")[0], "fully-forged-value.sig"):
        response = client.get(ME_PATH, cookies={"fdg_session": bad})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
    client.cookies.delete("fdg_session")  # no cookie at all
    assert client.get(ME_PATH).status_code == 401


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"username": "ada", "password": "wrong"}, 401),
        ({"username": "ghost", "password": "analytical-engine"}, 401),
        ({"username": "", "password": "x"}, 422),
        ({"username": "ada"}, 422),
    ],
)
def test_login_refusals(client: TestClient, payload: dict[str, str], status: int) -> None:
    response = client.post(LOGIN_PATH, json=payload)
    assert response.status_code == status
    if status == 401:
        assert response.json()["error"]["code"] == "unauthorized"


def test_logout_is_idempotent(client: TestClient) -> None:
    first = client.post(LOGOUT_PATH).json()
    second = client.post(LOGOUT_PATH).json()
    assert first["revoked"] is False and second["revoked"] is False
