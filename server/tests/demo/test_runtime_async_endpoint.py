"""GET /api/demo/runtime/async: the endpoint's payload contract.

The endpoint awaits the real builder, so its timings are measured per
request. These tests pin the wire shape (camelCase keys), the deterministic
orderings, and the physical timing invariants with generous headroom.
"""

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/runtime/async"


def _payload(client: TestClient) -> dict[str, object]:
    response = client.get(DEMO_PATH)
    assert response.status_code == 200
    return response.json()


def test_returns_200_typed_payload(client: TestClient) -> None:
    body = _payload(client)
    assert set(body) == {"ioPlan", "sequential", "gathered", "speedup", "trace"}
    assert [task["name"] for task in body["ioPlan"]] == ["orders", "billing", "inventory"]


def test_both_runs_carry_strategy_elapsed_and_per_task_timings(client: TestClient) -> None:
    body = _payload(client)
    for run, strategy in ((body["sequential"], "sequential"), (body["gathered"], "gathered")):
        assert run["strategy"] == strategy
        assert run["elapsedMs"] > 0
        assert [task["name"] for task in run["perTask"]] == [
            "orders",
            "billing",
            "inventory",
        ]
        for task in run["perTask"]:
            assert task["measuredMs"] >= task["simulatedIoMs"] - 0.1


def test_completion_orders_differ_between_runs(client: TestClient) -> None:
    body = _payload(client)
    assert body["sequential"]["completionOrder"] == ["orders", "billing", "inventory"]
    assert body["gathered"]["completionOrder"] == ["inventory", "billing", "orders"]


def test_timings_present_and_gathered_beats_sequential(client: TestClient) -> None:
    body = _payload(client)
    sequential = body["sequential"]["elapsedMs"]
    gathered = body["gathered"]["elapsedMs"]
    assert isinstance(sequential, float) and sequential >= 120 - 0.1
    assert isinstance(gathered, float) and gathered >= 60 - 0.1
    assert gathered < sequential
    assert body["speedup"] > 1.3


def test_trace_interleaves_the_two_actors(client: TestClient) -> None:
    body = _payload(client)
    events = [f"{event['actor']}:{event['event']}" for event in body["trace"]]
    assert events == [
        "alpha:start",
        "beta:start",
        "alpha:step-0",
        "beta:step-0",
        "alpha:step-1",
        "beta:step-1",
        "alpha:step-2",
        "beta:step-2",
        "alpha:done",
        "beta:done",
    ]


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][DEMO_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("AsyncTimingPayload")
