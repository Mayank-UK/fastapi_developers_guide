"""The structured-log viewer endpoint (topic 33, area ``obs``).

Pins the wire contract (GET /api/demo/obs/viewer): the pipeline rows are
the LIVE structlog chain introspected from the process configuration, the
level row carries the config's real log level with its real source, and
every event row is a REAL structured event the process logged — including
the panel request's own two beats, stamped with the very request id the
response's x-request-id header echoes. Correlation is pinned end to end:
a 404 driven with a known inbound id first must surface in the panel's
events as the access-log row and the failure row, sharing that id.
"""

from typing import Any

from fastapi.testclient import TestClient

VIEWER_PATH = "/api/demo/obs/viewer"

EXPECTED_PIPELINE = [
    "merge_contextvars",
    "add_log_level",
    "TimeStamper",
    "ExceptionRenderer",
    "RecentLog.capture",
    "JSONRenderer",
]


def fields_of(event: dict[str, Any]) -> dict[str, str]:
    """One event row's field pairs, keyed by name."""
    return {field["name"]: field["value"] for field in event["fields"]}


def test_the_pipeline_is_introspected_live_in_execution_order(client: TestClient) -> None:
    body = client.get(VIEWER_PATH).json()
    assert [stage["processor"] for stage in body["pipeline"]] == EXPECTED_PIPELINE
    assert [stage["orderIndex"] for stage in body["pipeline"]] == list(range(6))
    roles = {stage["processor"]: stage["role"] for stage in body["pipeline"]}
    assert "request id" in roles["merge_contextvars"]
    assert "ring" in roles["RecentLog.capture"]
    assert body["pipelineNote"]


def test_the_level_row_carries_the_real_configured_level(client: TestClient) -> None:
    body = client.get(VIEWER_PATH).json()
    assert body["configuredLevel"] == "info"  # the dev default, no FDG_LOG_LEVEL set
    assert "FDG_LOG_LEVEL" in body["levelSource"]
    assert body["ringCapacity"] == 50


def test_the_panel_logs_its_own_beats_with_the_response_request_id(
    client: TestClient,
) -> None:
    response = client.get(VIEWER_PATH)
    assert response.status_code == 200
    body = response.json()
    request_id = response.headers["x-request-id"]

    assert body["panelRequestId"] == request_id
    own = [event for event in body["events"] if event["requestId"] == request_id]
    by_event = {event["event"]: event for event in own}
    assert by_event["obs_viewer_panel_opened"]["level"] == "info"
    assert fields_of(by_event["obs_viewer_panel_opened"])["panel"] == "obs:viewer"
    assert by_event["obs_viewer_sample_warning"]["level"] == "warning"
    assert "warning-level beat" in fields_of(by_event["obs_viewer_sample_warning"])["detail"]


def test_a_driven_404_surfaces_in_the_events_with_its_request_id(
    client: TestClient,
) -> None:
    failed = client.get("/api/posts/nope", headers={"x-request-id": "viewer-correlation-404"})
    assert failed.status_code == 404
    body = client.get(VIEWER_PATH).json()

    correlated = [
        event for event in body["events"] if event["requestId"] == "viewer-correlation-404"
    ]
    events = {event["event"]: event for event in correlated}
    # The access-log line and the failure row, one id tying them together.
    assert events["app_error"]["level"] == "warning"
    assert fields_of(events["app_error"])["kind"] == "not_found"
    assert fields_of(events["http_request"])["status"] == "404"
    assert fields_of(events["http_request"])["path"] == "/api/posts/nope"
    # Events are served oldest first with strictly increasing sequences.
    sequences = [event["sequence"] for event in body["events"]]
    assert sequences == sorted(sequences)


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][VIEWER_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("LogViewerPanel")
