"""The stall-diagnosis endpoint (topic 35, area ``debug``).

Pins the wire contract (GET /api/demo/debug/stall): four bounded phases in
a fixed order, each carrying REAL measurements — elapsed from
perf_counter, loop lag from the concurrent probe's sleep overshoot, and a
concurrent REAL internal GET /api/health driven through the app mid-phase.
Timing asserts are deliberately RELATIVE or generously floored (shared CI
hardware is noisy; the starvation contrast is physics: a blocked loop
cannot fire timers). The self-limiting contract is pinned too: the
phases' total is bounded and an immediate /api/health after the demo
still answers promptly — the demo never wedges the shared loop.
"""

from typing import Any

from fastapi.testclient import TestClient

STALL_PATH = "/api/demo/debug/stall"

PHASE_LABELS = ["baseline", "async-await-stall", "blocking-in-threadpool", "blocking-on-loop"]


def row_by_label(body: dict[str, Any], label: str) -> dict[str, Any]:
    """The phase row carrying ``label``."""
    return next(row for row in body["phases"] if row["label"] == label)


def test_serves_the_four_phases_in_order_with_real_health_probes(client: TestClient) -> None:
    response = client.get(STALL_PATH)
    assert response.status_code == 200
    body = response.json()
    assert [row["label"] for row in body["phases"]] == PHASE_LABELS
    for row in body["phases"]:
        assert row["elapsedMs"] >= 0.0
        assert row["loopLagMaxMs"] >= 0.0
        assert row["concurrentHealthStatus"] == 200, "the concurrent probe hit the real route"
        assert row["verdict"]
    assert body["pySpyNote"]
    assert body["honestyNote"]


def test_the_on_loop_block_starves_where_the_threadpool_does_not(client: TestClient) -> None:
    body = client.get(STALL_PATH).json()
    on_loop = row_by_label(body, "blocking-on-loop")
    threadpool = row_by_label(body, "blocking-in-threadpool")
    async_row = row_by_label(body, "async-await-stall")
    assert on_loop["loopLagMaxMs"] > threadpool["loopLagMaxMs"]
    assert on_loop["loopLagMaxMs"] >= 40.0
    assert on_loop["concurrentHealthMs"] > async_row["concurrentHealthMs"]
    assert on_loop["concurrentHealthStatus"] == 200
    # The block itself is bounded: the on-loop phase lasts about its budget.
    assert on_loop["elapsedMs"] < 400.0


def test_the_async_stall_is_slow_for_the_request_and_fast_for_everyone_else(
    client: TestClient,
) -> None:
    body = client.get(STALL_PATH).json()
    async_row = row_by_label(body, "async-await-stall")
    baseline = row_by_label(body, "baseline")
    assert async_row["elapsedMs"] >= 350.0, "the bounded await must actually elapse"
    assert baseline["elapsedMs"] < async_row["elapsedMs"]
    # 350ms of awaiting left the loop free: health answered far inside the stall.
    assert async_row["concurrentHealthMs"] < async_row["elapsedMs"]


def test_the_panel_correlates_with_its_own_request_id(client: TestClient) -> None:
    response = client.get(STALL_PATH)
    body = response.json()
    assert body["panelRequestId"] == response.headers["x-request-id"]
    assert body["logEvents"], "the panel left no correlated log rows"
    assert all(event["requestId"] == body["panelRequestId"] for event in body["logEvents"])
    events = [event["event"] for event in body["logEvents"]]
    assert events.count("debug_stall_phase") == 4, "one real beat per phase"


def test_the_tracemalloc_window_is_real(client: TestClient) -> None:
    body = client.get(STALL_PATH).json()
    allocations = body["allocations"]
    assert allocations["objects"] == 2000
    assert allocations["peakKb"] >= allocations["currentKb"] > 0.0
    assert "tracemalloc" in allocations["note"]


def test_the_demo_is_self_limiting_and_leaves_the_loop_responsive(client: TestClient) -> None:
    body = client.get(STALL_PATH).json()
    total = sum(row["elapsedMs"] for row in body["phases"])
    assert total < 2000.0, f"the demo must stay bounded, took {total}ms"
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.elapsed.total_seconds() < 1.0, "the loop must answer immediately after the demo"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][STALL_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("StallPanel")
