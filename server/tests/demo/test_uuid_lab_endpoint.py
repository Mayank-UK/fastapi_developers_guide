"""The UUID-lab endpoint: the comparison a curl away (no database)."""

from fastapi.testclient import TestClient

UUID_PATH = "/api/demo/db/uuid"


def test_the_lab_serves_the_three_runs_with_their_ordering_proofs(client: TestClient) -> None:
    body = client.get(UUID_PATH).json()
    assert body["sampleCount"] == 12
    runs = {run["kind"]: run for run in body["runs"]}
    assert set(runs) == {"uuid4", "uuid7", "sequence"}
    assert runs["uuid7"]["sortable"] is True
    assert runs["uuid7"]["sortRanks"] == list(range(12))
    assert runs["uuid4"]["sortable"] is False
    assert runs["sequence"]["sortable"] is False  # '10' sorts before '2' as text


def test_the_layout_is_a_real_uuid7_dissected(client: TestClient) -> None:
    body = client.get(UUID_PATH).json()
    layout = body["layout"]
    assert len(layout["segments"]) == 5
    assert layout["segments"][1]["hexValue"] == "7"
    assert layout["unixMs"] > 1_700_000_000_000  # a plausible 2020s timestamp
    assert layout["generatedAtIso"].startswith("20")
    assert body["sharedPrefixHex"]
    assert {card["id"] for card in body["strategies"]} == {"sequence", "uuid4", "uuid7"}


def test_the_endpoint_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/demo/db/uuid" in schema["paths"]
    assert "/api/demo/db/schema-explorer" in schema["paths"]
