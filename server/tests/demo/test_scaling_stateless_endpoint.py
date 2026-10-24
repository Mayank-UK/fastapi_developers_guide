"""The scaling-stateless endpoint (topic 40, area ``scaling``).

Pins the wire contract (GET /api/demo/scaling/stateless): the process
facts snapshot-read off the composition root, the nine-step two-replica
round (a process-local scenario write that never crosses to the second
replica, beside a REAL redis INCR round where the second increment's
answer contains the first's), the three verdict rows, the eleven-row
state-placement inventory naming the real holders, and the honesty note
that frames the two replicas as two state worlds inside one process.
The redis-backed tests run against the REAL dev-stack Redis (the
playground's posture); unreachable Redis degrades to the
service_unavailable envelope, and the openapi declaration is pinned with
the plain client.
"""

import pytest
from fastapi.testclient import TestClient
from redis_url import COMPOSE_REDIS_URL

from guide.core.config import get_config
from guide.main import create_app

STATELESS_PATH = "/api/demo/scaling/stateless"

UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1"

PROCESS_ROW_IDS = ["processes", "pid", "scenario-now", "posts-now"]
VERDICT_ROW_IDS = ["in-process", "externalized", "the-trade"]
INVENTORY_ROW_IDS = [
    "posts-substrate",
    "scenario-store",
    "auth-state",
    "rate-limiter",
    "chat-rooms",
    "cache-service",
    "postgres",
    "redis",
    "mongo",
    "session-cookie",
    "jwt",
]
EXPECTED_SIDES = [
    "process",
    "replica-a",
    "replica-a",
    "replica-b",
    "replica-b",
    "shared",
    "replica-a",
    "replica-b",
    "shared",
]


@pytest.fixture
def redis_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_serves_the_process_facts_snapshot(redis_client: TestClient) -> None:
    response = redis_client.get(STATELESS_PATH)
    assert response.status_code == 200
    body = response.json()
    assert [row["id"] for row in body["process"]] == PROCESS_ROW_IDS
    processes = next(r for r in body["process"] if r["id"] == "processes")["value"]
    assert "1 — the dev stack runs uvicorn --reload" in processes
    pid = next(r for r in body["process"] if r["id"] == "pid")["value"]
    assert "heap" in pid
    scenario = next(r for r in body["process"] if r["id"] == "scenario-now")["value"]
    assert "dataMode=fake" in scenario and "injectFailure=none" in scenario
    posts = next(r for r in body["process"] if r["id"] == "posts-now")["value"]
    assert "12 of them the deterministic seed" in posts


def test_the_round_is_nine_steps_with_the_patch_never_crossing(
    redis_client: TestClient,
) -> None:
    body = redis_client.get(STATELESS_PATH).json()
    steps = body["replicaRound"]
    assert [s["step"] for s in steps] == list(range(1, 10))
    assert [s["side"] for s in steps] == EXPECTED_SIDES
    # The in-process half: A patches, B — built identically — never sees it.
    assert steps[2]["observed"] == "dataMode=fake · injectFailure=latency"
    assert steps[4]["observed"].endswith("A's patch is invisible")
    assert "process-local state does not follow" in steps[4]["detail"]
    # The externalized half: one key, two increments, the second includes the first.
    assert steps[6]["observed"] == "INCR → 1"
    assert steps[7]["observed"] == "INCR → 2 — externalized state follows the request"
    assert steps[8]["observed"] == "value 2 with a 60s self-cleaning ttl"
    assert "guide_demo:scaling:shared" in steps[5]["detail"]


def test_the_round_is_deterministic_on_every_request(redis_client: TestClient) -> None:
    first = redis_client.get(STATELESS_PATH).json()["replicaRound"]
    second = redis_client.get(STATELESS_PATH).json()["replicaRound"]
    assert first[6]["observed"] == second[6]["observed"] == "INCR → 1"
    assert first[7]["observed"] == second[7]["observed"]


def test_the_verdicts_state_the_contrast_and_the_trade(redis_client: TestClient) -> None:
    body = redis_client.get(STATELESS_PATH).json()
    rows = {row["id"]: row for row in body["verdicts"]}
    assert list(rows) == VERDICT_ROW_IDS
    assert "invisible to replica B" in rows["in-process"]["value"]
    assert "returned 2" in rows["externalized"]["value"]
    assert "load balancer" in rows["the-trade"]["value"]


def test_the_inventory_places_every_real_store(redis_client: TestClient) -> None:
    body = redis_client.get(STATELESS_PATH).json()
    rows = {row["id"]: row for row in body["inventory"]}
    assert list(rows) == INVENTORY_ROW_IDS
    placements = {row_id: rows[row_id]["placement"] for row_id in rows}
    assert placements["posts-substrate"] == "in-process"
    assert placements["scenario-store"] == "in-process"
    assert placements["auth-state"] == "in-process"
    assert placements["rate-limiter"] == "in-process"
    assert placements["chat-rooms"] == "in-process"
    assert placements["cache-service"] == "in-process"
    assert placements["postgres"] == "externalized"
    assert placements["redis"] == "externalized"
    assert placements["mongo"] == "externalized"
    assert placements["session-cookie"] == "client-side"
    assert placements["jwt"] == "client-side"
    # Live-evidenced rows read from THIS app: the posts count and the counter proof.
    assert "posts in this process right now" in rows["posts-substrate"]["evidence"]
    assert "held 2 after both replicas wrote" in rows["redis"]["evidence"]
    # The in-process restart story is honest: the seed survives, the rest does not.
    assert "created since boot is gone" in rows["posts-substrate"]["restart"]
    assert "defaults" in rows["scenario-store"]["restart"]


def test_the_honesty_note_names_the_construction(redis_client: TestClient) -> None:
    note = redis_client.get(STATELESS_PATH).json()["honestyNote"]
    assert "two state worlds inside this one process" in note
    assert "real redis INCR" in note
    assert "its own create_app" in note


def test_the_panel_is_bounded(redis_client: TestClient) -> None:
    response = redis_client.get(STATELESS_PATH)
    assert response.elapsed.total_seconds() < 5.0, (
        "three redis commands and two constructor calls — nothing sleeps"
    )


def test_unreachable_redis_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(STATELESS_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert "shared counter" in response.json()["error"]["message"]


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][STATELESS_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("StatelessPanel")
