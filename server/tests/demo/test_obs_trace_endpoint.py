"""The trace fan-out endpoint (topic 33, area ``obs``).

Pins the wire contract (GET /api/demo/obs/trace): three REAL internal
rounds driven through the live app at the ASGI boundary, one per outcome
class (a clean 200, the posts resource's 404, FastAPI's query validation
422), each carrying an inbound request id DERIVED from the panel request's
own id — shared root prefix, per-round suffix. Every correlation claim is
pinned: the echoed response header, the error envelope's requestId, and
the log rows the round produced (access-log line + failure row for the
failed rounds) all agree on one id per round; the healthy round carries
exactly its access-log line and no failure row.
"""

from typing import Any

from fastapi.testclient import TestClient

TRACE_PATH = "/api/demo/obs/trace"

EXPECTED_ROUNDS = [
    ("ok", 200, None),
    ("not-found", 404, "not_found"),
    ("validation", 422, "validation_failed"),
]


def fields_of(event: dict[str, Any]) -> dict[str, str]:
    """One log-event row's field pairs, keyed by name."""
    return {field["name"]: field["value"] for field in event["fields"]}


def test_three_real_rounds_one_per_outcome_class(client: TestClient) -> None:
    response = client.get(TRACE_PATH)
    assert response.status_code == 200
    body = response.json()

    assert [(r["label"], r["status"], r["envelopeCode"]) for r in body["rounds"]] == EXPECTED_ROUNDS
    for round_ in body["rounds"]:
        assert round_["headerEchoed"] is True
        assert round_["durationMs"] >= round_["firstByteMs"] >= 0.0
        assert round_["requestLine"].startswith("GET /api/")


def test_child_ids_derive_from_the_panel_requests_own_id(client: TestClient) -> None:
    response = client.get(TRACE_PATH)
    body = response.json()
    root = response.headers["x-request-id"]

    assert body["rootRequestId"] == root
    for round_ in body["rounds"]:
        assert round_["inboundRequestId"] == f"{root[:24]}-{round_['label']}"
    assert "trace root" in body["derivedIdConvention"]


def test_failed_rounds_correlate_header_envelope_and_log_rows(client: TestClient) -> None:
    body = client.get(TRACE_PATH).json()
    by_label = {round_["label"]: round_ for round_ in body["rounds"]}

    for label, expected_code in (("not-found", "not_found"), ("validation", "validation_failed")):
        round_ = by_label[label]
        assert round_["envelopeCode"] == expected_code
        # The envelope's requestId IS the round's inbound id.
        assert round_["envelopeRequestId"] == round_["inboundRequestId"]
        # Every log row the round produced carries the same id.
        assert round_["logEvents"], f"{label} round left no log rows"
        assert all(e["requestId"] == round_["inboundRequestId"] for e in round_["logEvents"])
        events = {event["event"]: event for event in round_["logEvents"]}
        # The access-log line + the failure row, one id tying them together.
        assert fields_of(events["http_request"])["status"] == str(round_["status"])
        failure_event = "app_error" if label == "not-found" else "request_validation_failed"
        failure = events[failure_event]
        assert failure["level"] == ("warning" if label == "not-found" else "info")


def test_the_healthy_round_is_lone_access_log_row_no_failure(client: TestClient) -> None:
    body = client.get(TRACE_PATH).json()
    ok_round = next(round_ for round_ in body["rounds"] if round_["label"] == "ok")

    assert ok_round["envelopeCode"] is None
    assert ok_round["envelopeRequestId"] is None
    assert [event["event"] for event in ok_round["logEvents"]] == ["http_request"]
    assert ok_round["logEvents"][0]["level"] == "info"
    assert "no failure row" in ok_round["note"]


def test_the_notes_and_honesty_text_are_served(client: TestClient) -> None:
    body = client.get(TRACE_PATH).json()
    assert "Three places, one id" in body["correlationNote"]
    assert "NOT a dependency" in body["honestyNote"]
    assert "measured" in body["honestyNote"]


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][TRACE_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("TraceFanout")
