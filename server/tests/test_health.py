"""GET /api/health — status, exact payload shape, and the OpenAPI contract."""

from fastapi.testclient import TestClient

HEALTH_PATH = "/api/health"


def test_health_returns_200(client: TestClient) -> None:
    response = client.get(HEALTH_PATH)
    assert response.status_code == 200


def test_health_payload_shape(client: TestClient) -> None:
    response = client.get(HEALTH_PATH)
    assert response.json() == {"status": "ok", "env": "dev"}


def test_health_response_model_declared(client: TestClient) -> None:
    """The route must publish HealthResponse in OpenAPI (the API contract)."""
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][HEALTH_PATH]["get"]
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"] == "#/components/schemas/HealthResponse"
    assert "HealthResponse" in schema["components"]["schemas"]
