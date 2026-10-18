"""The sql-safety endpoint over the REAL dev PostgreSQL.

``GET /api/demo/db/sql-safety`` must run the parameterized filter for
real — the default input is the canonical injection payload, and the
proof of safety is that it matches ZERO rows while arriving intact as
the bind parameter's value — while the unsafe card carries the
interpolated text with ``executed: false``. A benign filter returns
real rows; an over-long filter is refused at the edge (422); an
unreachable PostgreSQL answers the 503 envelope.
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

SAFETY_PATH = "/api/demo/db/sql-safety"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A TestClient whose app config points at the dev compose PostgreSQL."""
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:  # entering runs the lifespan (migrations)
        yield client


def test_the_default_injection_payload_is_neutralized_as_data(pg_client: TestClient) -> None:
    body = pg_client.get(SAFETY_PATH).json()
    assert body["filterValue"] == "'; DROP TABLE posts; --"
    safe = body["safe"]
    assert safe["parameterName"] == "pattern"
    assert safe["parameterValue"] == "%'; DROP TABLE posts; --%"
    assert safe["rowCount"] == 0  # no title contains that as literal text
    assert ":pattern" in safe["sql"]
    # The posts table still very much exists — nothing was dropped.
    assert "posts" in safe["sql"]
    unsafe = body["unsafe"]
    assert unsafe["executed"] is False
    assert "DROP TABLE posts" in unsafe["renderedSql"]
    assert unsafe["renderedSql"].startswith("SELECT id, slug, title, status FROM posts")


def test_a_benign_filter_returns_real_rows(pg_client: TestClient) -> None:
    body = pg_client.get(SAFETY_PATH, params={"filter": "chapter"}).json()
    assert body["safe"]["rowCount"] >= 3  # the three drafting-the-*-chapter posts
    titles = [row["title"] for row in body["safe"]["rows"]]
    assert any("webhooks" in title.lower() for title in titles)
    assert body["unsafe"]["executed"] is False


def test_quotes_in_input_stay_data(pg_client: TestClient) -> None:
    body = pg_client.get(
        SAFETY_PATH, params={"filter": "envelope's"}
    ).json()
    assert body["safe"]["rowCount"] == 0  # a quote in the value breaks nothing
    assert "envelope's" in body["unsafe"]["renderedSql"]


def test_overlong_filter_is_refused_at_the_edge(pg_client: TestClient) -> None:
    response = pg_client.get(SAFETY_PATH, params={"filter": "x" * 201})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_unreachable_postgresql_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_DATABASE_URL", "postgresql+asyncpg://postgres:guide@127.0.0.1:1/guide")
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(SAFETY_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_endpoint_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/demo/db/sql-safety" in schema["paths"]
