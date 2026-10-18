"""GET /api/demo/runtime/streaming: the NDJSON stream contract.

Consumed through TestClient's streaming interface, line by line — the same
shape a real client sees: application/x-ndjson, one JSON object per line,
open → items → closed, deterministic count and order.
"""

import json

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/runtime/streaming"
EXPECTED_ITEMS = 6


def _lines(client: TestClient) -> list[str]:
    with client.stream("GET", DEMO_PATH) as response:
        assert response.status_code == 200
        content_type = response.headers["content-type"]
        assert content_type.startswith("application/x-ndjson")
        return [line for line in response.iter_lines() if line]


def test_streams_open_items_closed_lines(client: TestClient) -> None:
    chunks = [json.loads(line) for line in _lines(client)]
    assert [chunk["kind"] for chunk in chunks] == [
        "open",
        *["item"] * EXPECTED_ITEMS,
        "closed",
    ]
    assert [chunk["seq"] for chunk in chunks] == list(range(EXPECTED_ITEMS + 2))


def test_labels_and_closing_totals_are_present(client: TestClient) -> None:
    chunks = [json.loads(line) for line in _lines(client)]
    assert chunks[0]["label"] == "runtime-stream"
    assert chunks[3]["label"] == "loop-tick-3"
    closed = chunks[-1]
    assert closed["itemsDelivered"] == EXPECTED_ITEMS
    assert isinstance(closed["totalMs"], float) and closed["totalMs"] > 0


def test_two_reads_produce_the_same_shape(client: TestClient) -> None:
    first = [json.loads(line)["label"] for line in _lines(client)]
    second = [json.loads(line)["label"] for line in _lines(client)]
    assert first == second  # deterministic content; only totalMs may differ


def test_streaming_route_declares_no_json_payload_schema(client: TestClient) -> None:
    """StreamingResponse bypasses response_model; OpenAPI records no $ref schema."""
    schema = client.get("/openapi.json").json()
    response = schema["paths"][DEMO_PATH]["get"]["responses"]["200"]
    wire_schema = response.get("content", {}).get("application/json", {}).get("schema", {})
    assert "$ref" not in wire_schema
