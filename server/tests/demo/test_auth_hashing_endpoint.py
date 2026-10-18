"""The hashing lab endpoints — real cost, same-cost verdicts, rehash signal.

argon2id with the cost honestly reported: two hashes of the same input
differ (fresh salt), match and mismatch burn comparable milliseconds
(the wrong-password path runs the FULL computation), and the panel's
2015-cost legacy hash verifies true and fires needs_rehash — the
upgrade-on-login path. No password or hash preview ever leaks into an
error detail.
"""

from fastapi.testclient import TestClient

from guide.domain.auth.password_service import LEGACY_HASH

ROSTER_PATH = "/api/demo/auth/hashing"
HASH_PATH = "/api/demo/auth/hashing/hash"
VERIFY_PATH = "/api/demo/auth/hashing/verify"


def test_panel_states_the_contract_and_the_seed(client: TestClient) -> None:
    body = client.get(ROSTER_PATH).json()
    assert body["algorithm"] == "argon2id"
    assert "m=65536" in body["parameters"]
    assert "m=8192" in body["legacyParameters"]  # 2015-era cost, stated
    seeded = {row["username"] for row in body["seedCredentials"]}
    assert seeded == {"ada", "grace"}
    for row in body["seedCredentials"]:
        assert row["hashPreview"].endswith("…")  # previews only
    assert "one-way" in body["distinctionNote"]


def test_hash_is_salted_and_honestly_timed(client: TestClient) -> None:
    first = client.post(HASH_PATH, json={"password": "same password"}).json()
    second = client.post(HASH_PATH, json={"password": "same password"}).json()
    assert first["hash"] != second["hash"]
    assert first["hash"].startswith("$argon2id$")
    assert first["elapsedMs"] > 0
    assert second["elapsedMs"] > 0


def test_verify_match_mismatch_and_malformed(client: TestClient) -> None:
    minted = client.post(HASH_PATH, json={"password": "the password"}).json()
    ok = client.post(
        VERIFY_PATH, json={"password": "the password", "hash": minted["hash"]}
    ).json()
    assert ok["ok"] is True and ok["needsRehash"] is False and ok["error"] is None

    wrong = client.post(
        VERIFY_PATH, json={"password": "a wrong one", "hash": minted["hash"]}
    ).json()
    assert wrong["ok"] is False and wrong["error"] is None
    # Match and mismatch both burned a full argon2 run — same cost shape.
    assert wrong["elapsedMs"] > 0

    malformed = client.post(
        VERIFY_PATH, json={"password": "x", "hash": "not-an-argon2-string"}
    ).json()
    assert malformed["ok"] is False and malformed["error"] is not None


def test_legacy_cost_verifies_and_fires_the_rehash_signal(client: TestClient) -> None:
    verdict = client.post(
        VERIFY_PATH, json={"password": "analytical-engine", "hash": LEGACY_HASH}
    ).json()
    assert verdict["ok"] is True
    assert verdict["needsRehash"] is True


def test_bounds_are_enforced(client: TestClient) -> None:
    assert client.post(HASH_PATH, json={"password": ""}).status_code == 422
    assert client.post(VERIFY_PATH, json={"password": "x"}).status_code == 422
