"""The refresh lab endpoints — family birth, rotation, the reuse alarm.

One family's whole life over HTTP: login mints the first one-time token
(raw shown once), each exchange rotates (old flips to used, next link
minted), and replaying a used token trips reuse detection — the family
flips to revoked store-side, the kill count rides the response, and the
still-held current token dies with it. The board shows the timelines.
"""

from fastapi.testclient import TestClient

ROSTER_PATH = "/api/demo/auth/refresh"
LOGIN_PATH = "/api/demo/auth/refresh/login"
EXCHANGE_PATH = "/api/demo/auth/refresh/exchange"

ADA = {"username": "ada", "password": "analytical-engine"}


def _login(client: TestClient) -> dict[str, object]:
    response = client.post(LOGIN_PATH, json=ADA)
    assert response.status_code == 200
    return response.json()


def _exchange(client: TestClient, token: str):
    return client.post(EXCHANGE_PATH, json={"refreshToken": token})


def test_login_starts_a_family_with_the_token_shown_once(client: TestClient) -> None:
    login = _login(client)
    assert str(login["familyId"]).startswith("fam_")
    assert str(login["refreshToken"]).startswith("rt_")
    assert login["accessExpiresIn"] == 900

    board = client.get(ROSTER_PATH).json()
    assert board["telemetry"]["logins"] == 1
    family = board["families"][0]
    assert family["status"] == "active"
    assert [token["status"] for token in family["tokens"]] == ["active"]


def test_rotation_marks_used_and_mints_the_next_link(client: TestClient) -> None:
    login = _login(client)
    first = _exchange(client, str(login["refreshToken"]))
    assert first.status_code == 200
    rotated = first.json()
    assert rotated["outcome"] == "rotated"
    assert rotated["rotatedFromPosition"] == 1
    assert rotated["refreshToken"] != login["refreshToken"]

    second = _exchange(client, str(rotated["refreshToken"])).json()
    assert second["rotatedFromPosition"] == 2
    board = client.get(ROSTER_PATH).json()
    statuses = [token["status"] for token in board["families"][0]["tokens"]]
    assert statuses == ["used", "used", "active"]
    assert board["telemetry"]["rotations"] == 2


def test_replay_trips_the_alarm_and_kills_the_whole_family(client: TestClient) -> None:
    login = _login(client)
    first = _exchange(client, str(login["refreshToken"])).json()
    current = str(first["refreshToken"])

    replay = _exchange(client, str(login["refreshToken"]))
    assert replay.status_code == 200  # the alarm is a SUCCESS response
    alarm = replay.json()
    assert alarm["outcome"] == "reuse-detected"
    assert alarm["familyId"] == login["familyId"]
    assert alarm["familyTokensRevoked"] == 2  # positions 1 (used) and 2 (active)

    dead = _exchange(client, current)
    assert dead.status_code == 401
    assert dead.json()["error"]["code"] == "unauthorized"

    board = client.get(ROSTER_PATH).json()
    family = board["families"][0]
    assert family["status"] == "revoked"
    assert [token["status"] for token in family["tokens"]] == ["revoked", "revoked"]
    assert board["telemetry"]["reuseEvents"] == 1


def test_unknown_tokens_and_bad_credentials(client: TestClient) -> None:
    unknown = _exchange(client, "rt_never_issued_anywhere")
    assert unknown.status_code == 401
    assert unknown.json()["error"]["code"] == "unauthorized"

    wrong_password = client.post(
        LOGIN_PATH, json={"username": "ada", "password": "wrong"}
    )
    assert wrong_password.status_code == 401
    assert client.get(ROSTER_PATH).json()["families"] == []


def test_exchange_bounds_are_enforced(client: TestClient) -> None:
    assert client.post(EXCHANGE_PATH, json={"refreshToken": ""}).status_code == 422
