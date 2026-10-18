"""The schema-explorer endpoint over the REAL dev PostgreSQL.

``GET /api/demo/db/schema-explorer`` must introspect the live database
(the migration's tables, constraints, and indexes — nothing canned),
answer a drill-down with the full anatomy of one table, map an unknown
table to the honest 404 envelope, and degrade to the 503 envelope when
PostgreSQL is unreachable. These tests enter the app's lifespan, so the
startup-migration path itself runs first (idempotently, against the
real database).
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

EXPLORER_PATH = "/api/demo/db/schema-explorer"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A TestClient whose app config points at the dev compose PostgreSQL."""
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:  # entering runs the lifespan (migrations)
        yield client


def test_root_serves_the_live_guide_schema(pg_client: TestClient) -> None:
    body = pg_client.get(EXPLORER_PATH).json()
    assert body["databaseName"] == "guide"
    names = {table["name"] for table in body["tables"]}
    assert {"authors", "posts", "comments", "audit_log"} <= names
    assert "focus" not in body  # exclude_none drops it at the root
    posts = next(t for t in body["tables"] if t["name"] == "posts")
    assert posts["columnCount"] == 11  # 0001's nine + 0002's search_vector + 0003's version
    assert posts["indexCount"] == 5  # pk + slug unique + FK + partial + GIN (0002)


def test_table_drill_down_reports_the_full_posts_anatomy(pg_client: TestClient) -> None:
    body = pg_client.get(EXPLORER_PATH, params={"table": "posts"}).json()
    focus = body["focus"]
    columns = {c["name"]: c for c in focus["columns"]}
    # Types as PostgreSQL spells them, arrays included.
    assert columns["id"]["type"] == "bigint"
    assert columns["tags"]["type"] == "text[]"
    assert columns["author_id"]["type"] == "uuid"
    assert columns["created_at"]["type"] == "timestamp with time zone"
    # The sequence default, visible exactly as bigserial implements it.
    assert columns["id"]["default"].startswith("nextval('posts_id_seq'")
    assert columns["author_id"]["nullable"] is False
    assert columns["body"]["default"] == "''::text"
    # PK derived from the primary index; FK with its ON DELETE behavior.
    assert focus["primaryKey"] == ["id"]
    fk = focus["foreignKeys"][0]
    assert fk["referencesTable"] == "authors"
    assert fk["onDelete"] == "RESTRICT"
    # CHECK constraints with their definitions.
    checks = {c["name"]: c["definition"] for c in focus["checks"]}
    assert "ck_posts_status_domain" in checks
    assert "draft" in checks["ck_posts_status_domain"]
    # The partial index carries its WHERE clause; the FK index is plain.
    indexes = {i["name"]: i for i in focus["indexes"]}
    assert indexes["ix_posts_published_created_at"]["where"] is not None
    assert "published" in indexes["ix_posts_published_created_at"]["where"]
    assert indexes["ix_posts_author_id"]["kind"] == "btree"
    assert indexes["ix_posts_author_id"]["unique"] is False


def test_unknown_table_is_the_honest_404_envelope(pg_client: TestClient) -> None:
    response = pg_client.get(EXPLORER_PATH, params={"table": "no_such_table"})
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert "no_such_table" in error["message"]


def test_unreachable_postgresql_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_DATABASE_URL", "postgresql+asyncpg://postgres:guide@127.0.0.1:1/guide")
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)  # no lifespan needed: the reader runs per request
    response = client.get(EXPLORER_PATH)
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "service_unavailable"
    assert "PostgreSQL" in error["message"]
