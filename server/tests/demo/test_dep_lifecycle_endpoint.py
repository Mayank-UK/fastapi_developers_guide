"""GET /api/demo/dep/lifecycle + /lifecycle/log: the yield-dependency proof.

These tests pin the framework fact the demo exists to show, as data: one
wrapped request appends exactly setup → handler → response → teardown to
the span log, in strictly increasing sequence order — the teardown AFTER
the response, because FastAPI closes the request-scoped AsyncExitStack
only after the response has been sent. The ring bound is pinned too: the
log holds the LAST 20 events no matter how many requests fire.
"""

import pytest
from fastapi.testclient import TestClient

from guide.presentation.dependencies.request_span import SpanLog

LIFECYCLE_PATH = "/api/demo/dep/lifecycle"
LOG_PATH = "/api/demo/dep/lifecycle/log"

SPAN_BEATS = ["setup", "handler", "response", "teardown"]


def test_span_log_ring_rejects_empty_capacity_and_returns_copies() -> None:
    with pytest.raises(ValueError, match="capacity"):
        SpanLog(capacity=0)

    log = SpanLog(capacity=2)
    for sequence in range(3):
        log.append(f"span-{sequence}", "setup", at="t", offset_ms=0)
    held = log.tail()
    assert [event.sequence for event in held] == [1, 2]  # oldest evicted

    held.clear()  # a caller cannot corrupt the ring through tail()
    assert len(log.tail()) == 2


def test_lifecycle_returns_the_facts_the_handler_can_know(client: TestClient) -> None:
    response = client.get(LIFECYCLE_PATH)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"spanId", "setupAt", "handlerOffsetMs", "pendingEvents"}
    assert len(body["spanId"]) == 12
    assert body["setupAt"].endswith("+00:00")
    assert isinstance(body["handlerOffsetMs"], int)
    # The honest confession: teardown has not run while this body was built.
    assert body["pendingEvents"] == ["teardown"]


def test_log_proves_setup_handler_response_teardown_ordering(client: TestClient) -> None:
    first = client.get(LIFECYCLE_PATH).json()
    log = client.get(LOG_PATH).json()
    assert log["capacity"] == 20

    events = [event for event in log["events"] if event["spanId"] == first["spanId"]]
    assert [event["event"] for event in events] == SPAN_BEATS
    sequences = [event["sequence"] for event in events]
    assert sequences == sorted(sequences) and len(set(sequences)) == 4
    # The load-bearing assertion: the send moment is sequenced BEFORE teardown.
    beats = {event["event"]: event["sequence"] for event in events}
    assert beats["setup"] < beats["handler"] < beats["response"] < beats["teardown"]


def test_two_requests_leave_two_complete_spans_in_the_log(client: TestClient) -> None:
    spans = [client.get(LIFECYCLE_PATH).json()["spanId"] for _ in range(2)]
    assert spans[0] != spans[1]

    log = client.get(LOG_PATH).json()
    assert log["capacity"] == 20
    assert len(log["events"]) == 8  # 2 requests × 4 beats
    for span_id in spans:
        beats = [e["event"] for e in log["events"] if e["spanId"] == span_id]
        assert beats == SPAN_BEATS


def test_ring_keeps_only_the_last_twenty_events(client: TestClient) -> None:
    for _ in range(6):  # 6 requests × 4 beats = 24 appends
        client.get(LIFECYCLE_PATH)

    log = client.get(LOG_PATH).json()
    assert len(log["events"]) == 20
    sequences = [event["sequence"] for event in log["events"]]
    assert sequences == list(range(4, 24))  # oldest four evicted, order intact
    # Every held event belongs to a complete span: the ring keeps WHOLE beats
    # only because 20 divides by 4 — the bound is on events, not spans.
    assert all(
        any(e["spanId"] == event["spanId"] and e["event"] == "setup" for e in log["events"])
        for event in log["events"]
    )


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    lifecycle_ref = paths[LIFECYCLE_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert lifecycle_ref.endswith("DepLifecyclePayload")
    log_ref = paths[LOG_PATH]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert log_ref.endswith("SpanLogSnapshot")
