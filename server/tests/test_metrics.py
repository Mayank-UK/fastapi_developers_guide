"""GET /metrics — Prometheus exposition: status, content type, metric families."""

from fastapi.testclient import TestClient

METRICS_PATH = "/metrics"


def test_metrics_returns_200(client: TestClient) -> None:
    response = client.get(METRICS_PATH)
    assert response.status_code == 200


def test_metrics_content_type_is_prometheus_exposition(client: TestClient) -> None:
    """The scrape contract: the exposition format's registered content type."""
    response = client.get(METRICS_PATH)
    assert response.headers["content-type"] == "text/plain; version=1.0.0; charset=utf-8"


def test_metrics_body_exposes_default_metric_families(client: TestClient) -> None:
    """The default registry: the Python platform collector and the process collector."""
    body = client.get(METRICS_PATH).text
    assert "# HELP python_info" in body
    assert "process_cpu_seconds_total" in body


def test_metrics_not_in_openapi(client: TestClient) -> None:
    """A line protocol has no OpenAPI shape — the mount stays invisible, like /api/graphql."""
    schema = client.get("/openapi.json").json()
    assert METRICS_PATH not in schema["paths"]
