"""The jobs console endpoints: panel contract + boundary + honest degradation.

The panel and the boundary validation are pure (no store touched); the
store-backed endpoints run against the REAL dev Redis through the app's
own config rail (the family's stack-up posture — ``redis_url``), and
assert only what does not need the WORKER: the comparison's in-process
half (starlette runs BackgroundTasks inside TestClient's response
cycle, deterministically), the enqueue receipt, the mailbox compose
flow. The full worker walk — retries visible, dead letters, replay —
is the live smoke's proof (the worker container is not a test fixture).
"""

import pytest
from fastapi.testclient import TestClient
from redis_url import COMPOSE_REDIS_URL

from guide.core.config import get_config
from guide.main import create_app

CONSOLE_PATH = "/api/demo/jobs/console"
STATS_PATH = "/api/demo/jobs/stats"
DLQ_PATH = "/api/demo/jobs/dlq"
MAILBOX_PATH = "/api/demo/jobs/mailbox"
COMPARE_PATH = "/api/demo/jobs/compare"
RESET_PATH = "/api/demo/jobs/reset"

UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1"


@pytest.fixture
def redis_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A client whose app enqueues on the real dev Redis, cleaned per test."""
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client
        client.post(RESET_PATH)  # same portal/loop as the test itself


def test_the_panel_serves_the_policy_catalog_and_command(client: TestClient) -> None:
    body = client.get(CONSOLE_PATH).json()
    assert body["policy"]["maxAttempts"] == 3
    assert body["policy"]["strategy"] == "exponential"
    assert body["policy"]["attemptOffsets"] == [0, 0.25, 0.75]
    assert body["policy"]["delayBetweenAttempts"] == [0.25, 0.5]
    catalog_names = [row["name"] for row in body["catalog"]]
    assert catalog_names == ["fast", "fail_once", "fail_always", "slow", "send_email"]
    behaviors = {row["name"]: row["behavior"] for row in body["catalog"]}
    assert behaviors["fail_once"] == "succeeds-on-retry"
    assert behaviors["fail_always"] == "exhausts-retries"
    assert body["workerCommand"] == "arq guide.worker.WorkerSettings"
    assert "heartbeat" in body["cronSchedule"]
    assert any("real broker" in note for note in body["honestyNotes"])


def test_unknown_job_names_fail_at_the_boundary_with_an_envelope(client: TestClient) -> None:
    response = client.post("/api/demo/jobs/enqueue/not_a_job")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert "fail_once" in error["message"]  # the legal vocabulary, in the message


def test_enqueue_answers_a_ticket_for_the_real_queue(redis_client: TestClient) -> None:
    response = redis_client.post("/api/demo/jobs/enqueue/fast")
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["functionName"] == "fast"
    assert ticket["jobId"] and ticket["enqueuedAtMs"] > 0
    # The snapshot answers (any live state) with the envelope intact.
    snapshot = redis_client.get(f"/api/demo/jobs/jobs/{ticket['jobId']}")
    assert snapshot.status_code == 200
    assert snapshot.json()["jobId"] == ticket["jobId"]


def test_the_comparison_fires_both_halves_and_the_in_process_half_lands(
    redis_client: TestClient,
) -> None:
    fired = redis_client.post(COMPARE_PATH).json()
    assert fired["queuedJobId"] and fired["runId"]
    assert 0 <= fired["handlerDurationMs"] < 5_000

    ledger = redis_client.get(COMPARE_PATH).json()["runs"]
    in_process = [run for run in ledger if run["runId"] == fired["runId"]]
    # TestClient runs BackgroundTasks inside the response cycle: deterministic.
    assert len(in_process) == 1
    row = in_process[0]
    assert row["side"] == "in_process"
    assert "BackgroundTasks" in row["ranOn"]
    assert row["handoffDurationMs"] >= 0
    assert 0 < row["workDurationMs"] < 5_000


def test_the_mailbox_compose_flow_enqueues_the_email_job(redis_client: TestClient) -> None:
    response = redis_client.post(
        MAILBOX_PATH, json={"to": "ada@example.com", "subject": "hello", "body": "test"}
    )
    assert response.status_code == 201
    assert response.json()["functionName"] == "send_email"


def test_the_mailbox_validates_shape_at_the_boundary(redis_client: TestClient) -> None:
    assert (
        redis_client.post(MAILBOX_PATH, json={"to": "ab", "subject": "hi"}).status_code == 422
    )
    # A not-an-address is accepted on purpose: the worker parks it as poison.
    assert (
        redis_client.post(
            MAILBOX_PATH, json={"to": "not-an-address", "subject": "hi"}
        ).status_code
        == 201
    )


def test_the_dlq_and_stats_endpoints_serve_their_shapes(redis_client: TestClient) -> None:
    dlq = redis_client.get(DLQ_PATH).json()
    assert "entries" in dlq and "replay" in dlq["detail"]
    stats = redis_client.get(STATS_PATH).json()
    assert stats["depth"] >= 0
    assert stats["oldestAgeSeconds"] is None or stats["oldestAgeSeconds"] >= 0


def test_unreachable_redis_degrades_to_the_service_unavailable_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The app still BOOTS with redis down (the optional-service discipline);
    # only the store-backed endpoints degrade — to the 503 envelope, while
    # the pure panel keeps serving.
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    with TestClient(create_app()) as unreachable:
        get_config.cache_clear()
        response = unreachable.get(STATS_PATH)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "service_unavailable"
        assert unreachable.get(CONSOLE_PATH).status_code == 200
