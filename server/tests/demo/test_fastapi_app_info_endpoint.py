"""GET /api/demo/fastapi/app-info: the introspection endpoint's contract.

The endpoint runs the real builder against the REAL app (the test
fixture's own create_app), so these tests pin the payload against the
app serving it: identity + environment, the default docs mounts, the
route table including the endpoint itself and /api/health with GET,
the registered middleware, the handler kinds, and the declared response
model in OpenAPI.
"""

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/fastapi/app-info"


def test_serves_identity_environment_and_default_docs_mounts(client: TestClient) -> None:
    response = client.get(DEMO_PATH)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "FastAPI Developers Guide"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "dev"
    assert body["docs"] == {
        "docsUrl": "/docs",
        "redocUrl": "/redoc",
        "openapiUrl": "/openapi.json",
    }


def test_stack_names_the_three_libraries(client: TestClient) -> None:
    stack = client.get(DEMO_PATH).json()["stack"]
    assert set(stack) == {"fastapi", "starlette", "pydantic"}
    assert all(isinstance(value, str) and value for value in stack.values())


def test_route_table_is_sorted_and_includes_the_demo_itself(client: TestClient) -> None:
    routes = client.get(DEMO_PATH).json()["routes"]
    paths = [route["path"] for route in routes]
    assert paths == sorted(paths)
    by_path = {route["path"]: route for route in routes}
    assert by_path["/api/health"]["methods"] == ["GET"]
    assert by_path["/api/health"]["tags"] == ["health"]
    assert by_path["/api/demo/fastapi/app-info"]["methods"] == ["GET"]
    assert by_path["/api/demo/http/headers"]["methods"] == ["GET", "POST"]
    # Declared API surface only: the docs mounts are reported separately.
    assert "/docs" not in by_path
    assert "/openapi.json" not in by_path


def test_reports_the_registered_middleware_and_handler_kinds(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert body["middleware"] == [
        "CORSMiddleware",
        "SecurityHeadersMiddleware",
        "RequestLogMiddleware",
        "RequestIdMiddleware",
    ]
    handlers = {entry["exception"]: entry["handler"] for entry in body["exceptionHandlers"]}
    assert handlers["AppError"] == "handle_app_error"
    assert handlers["Exception"] == "handle_unexpected_error"
    assert handlers["HTTPException"] == "handle_http_exception"
    assert handlers["RequestValidationError"] == "handle_request_validation_error"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][DEMO_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("FastApiAppInfoPayload")


def test_request_id_round_trip(client: TestClient) -> None:
    response = client.get(DEMO_PATH, headers={"x-request-id": "app-info-probe"})
    assert response.headers["x-request-id"] == "app-info-probe"
