"""GET /api/demo/middleware/pipeline: the live chain's contract.

The endpoint runs the real engine against the REAL app (the test
fixture's own create_app), so these tests pin the payload against the
app serving it: the live stack walk (framework bookends, the user
layers — request ids plus topic 25's security pair, CORS outermost —
and the router terminal), the traced onion order, the request-id
round trip through the real middleware (payload field == response
header, inbound ids honored), and the declared response model.
"""

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/middleware/pipeline"

EXPECTED_STACK = [
    "ServerErrorMiddleware",
    "ExceptionTelemetryMiddleware",
    "CORSMiddleware",
    "SecurityHeadersMiddleware",
    "RequestIdMiddleware",
    "ExceptionMiddleware",
    "AsyncExitStackMiddleware",
    "APIRouter",
]
"""The built chain, outermost first — grown with topic 25's security pair
(CORS outermost so its verdict rides even error envelopes)."""


def test_serves_the_live_stack_in_request_order(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert [layer["name"] for layer in body["stack"]] == EXPECTED_STACK
    assert [layer["orderIndex"] for layer in body["stack"]] == list(range(len(EXPECTED_STACK)))
    kinds = {layer["name"]: layer["kind"] for layer in body["stack"]}
    assert kinds["RequestIdMiddleware"] == "user"
    assert kinds["CORSMiddleware"] == "user"
    assert kinds["SecurityHeadersMiddleware"] == "user"
    assert kinds["APIRouter"] == "router"
    assert kinds["ServerErrorMiddleware"] == "framework"
    roles = {layer["name"]: layer["role"] for layer in body["stack"]}
    assert all(role for role in roles.values())


def test_trace_proves_the_onion_order(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    events = body["trace"]
    layers_before_router = len(EXPECTED_STACK) - 1
    assert len(events) == 2 * layers_before_router + 1
    assert [event["sequence"] for event in events] == list(range(len(events)))
    assert [event["phase"] for event in events] == ["request"] * layers_before_router + [
        "handler"
    ] + ["response"] * layers_before_router
    stages = [event["stage"] for event in events]
    assert stages == EXPECTED_STACK[:-1] + ["APIRouter"] + list(
        reversed(EXPECTED_STACK[:-1])
    )


def test_request_side_and_response_side_orders_mirror_the_stack(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert body["requestSideOrder"] == EXPECTED_STACK
    assert body["responseSideOrder"] == list(reversed(EXPECTED_STACK))


def test_payload_request_id_equals_the_response_header(client: TestClient) -> None:
    response = client.get(DEMO_PATH)
    body = response.json()
    assert body["requestId"]
    assert body["requestIdHeader"] == "x-request-id"
    assert response.headers["x-request-id"] == body["requestId"]
    assert "requestId field" in body["reasoning"]


def test_inbound_request_id_is_honored_end_to_end(client: TestClient) -> None:
    response = client.get(DEMO_PATH, headers={"x-request-id": "middleware-probe"})
    assert response.json()["requestId"] == "middleware-probe"
    assert response.headers["x-request-id"] == "middleware-probe"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][DEMO_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("MiddlewarePipelinePayload")
