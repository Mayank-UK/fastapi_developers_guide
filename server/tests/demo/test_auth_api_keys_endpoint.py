"""The key lab endpoints — generate, protected call, revoke, roster.

The raw key appears exactly once (in the creation response; the roster
carries only prefixes and hash previews), the protected call
authenticates the x-api-key header or answers the 401 envelope for every
failure shape, and revocation is an instant prefix-keyed delete.
"""

import pytest
from fastapi.testclient import TestClient

ROSTER_PATH = "/api/demo/auth/keys"
CALL_PATH = "/api/demo/auth/keys/call"
REVOKE_PATH = "/api/demo/auth/keys/revoke"


def _generate(client: TestClient, name: str = "test key") -> dict[str, object]:
    response = client.post(ROSTER_PATH, json={"name": name, "scopes": ["posts:read"]})
    assert response.status_code == 200
    return response.json()


def test_generate_shows_the_raw_key_once_and_hash_at_rest(client: TestClient) -> None:
    created = _generate(client)
    assert str(created["prefix"]).startswith("fdg_")
    key = str(created["key"])
    assert key.startswith(str(created["prefix"]) + ".")
    assert len(key.split(".")[1]) >= 40  # the high-entropy half

    roster = client.get(ROSTER_PATH).json()
    assert [row["prefix"] for row in roster["records"]] == [created["prefix"]]
    record = roster["records"][0]
    assert "keyHashPreview" in record and record["keyHashPreview"].endswith("…")
    assert key not in roster["reasoning"]  # never the raw secret again
    assert roster["records"][0]["scopes"] == ["posts:read"]


def test_call_authenticates_the_header(client: TestClient) -> None:
    created = _generate(client)
    response = client.post(CALL_PATH, headers={"x-api-key": str(created["key"])})
    assert response.status_code == 200
    body = response.json()
    assert body["prefix"] == created["prefix"]
    assert body["name"] == "test key"
    assert body["scopes"] == ["posts:read"]


@pytest.mark.parametrize(
    "bad_key",
    [
        "fdg_deadbeef.not-the-real-secret-at-all",
        "no-separator",
        "",
    ],
)
def test_call_rejects_bad_keys_with_the_envelope(client: TestClient, bad_key: str) -> None:
    _generate(client)
    response = client.post(CALL_PATH, headers={"x-api-key": bad_key})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_call_without_header_is_unauthorized_not_422(client: TestClient) -> None:
    response = client.post(CALL_PATH)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_revoke_kills_every_copy_instantly(client: TestClient) -> None:
    created = _generate(client)
    assert client.post(CALL_PATH, headers={"x-api-key": str(created["key"])}).status_code == 200
    revoked = client.post(REVOKE_PATH, json={"prefix": created["prefix"]}).json()
    assert revoked["revoked"] is True
    assert client.get(ROSTER_PATH).json()["records"] == []
    dead = client.post(CALL_PATH, headers={"x-api-key": str(created["key"])})
    assert dead.status_code == 401
    unknown = client.post(REVOKE_PATH, json={"prefix": created["prefix"]})
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"


def test_request_bounds_are_enforced(client: TestClient) -> None:
    assert client.post(ROSTER_PATH, json={"name": ""}).status_code == 422
    assert client.post(ROSTER_PATH, json={"scopes": []}).status_code == 422
    assert client.post(REVOKE_PATH, json={"prefix": ""}).status_code == 422
