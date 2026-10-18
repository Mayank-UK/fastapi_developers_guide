"""The audit endpoint over the REAL dev PostgreSQL.

``GET /api/demo/db/audit`` proves the in-transaction audit pattern live:
the committed half reads its audit row back from the table, the
rolled-back half adds ZERO audit rows (counted, not claimed) and leaves
the attempted title invisible, and the post's audit history grows by
exactly one row per run.
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

AUDIT_PATH = "/api/demo/db/audit"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_the_committed_half_reads_its_audit_row_back(pg_client: TestClient) -> None:
    body = pg_client.get(AUDIT_PATH).json()
    committed = body["committed"]
    assert committed["changeVisible"] is True
    assert {committed["statusBefore"], committed["statusAfter"]} == {"draft", "published"}
    audit_row = committed["auditRow"]
    assert audit_row["actor"] == "demo:db-audit"
    assert audit_row["action"] == "update"
    assert "status:" in audit_row["changes"]
    assert audit_row["occurredAt"]


def test_the_rolled_back_half_leaves_no_trace(pg_client: TestClient) -> None:
    body = pg_client.get(AUDIT_PATH).json()
    rolled_back = body["rolledBack"]
    assert rolled_back["auditRowsAdded"] == 0  # measured before and after
    assert rolled_back["changeVisible"] is False
    assert "characters" in rolled_back["attemptedTitle"]  # truncated for display
    assert "ck_posts_title_length" in rolled_back["failure"]


def test_history_grows_by_exactly_one_row_per_run(pg_client: TestClient) -> None:
    first = pg_client.get(AUDIT_PATH).json()
    second = pg_client.get(AUDIT_PATH).json()
    assert second["historyCount"] == first["historyCount"] + 1
    assert first["history"][-1]["id"] == first["committed"]["auditRow"]["id"]
    # The status flip alternates — every run is itself audited.
    assert first["committed"]["statusAfter"] == second["committed"]["statusBefore"]


def test_unreachable_postgresql_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_DATABASE_URL", "postgresql+asyncpg://postgres:guide@127.0.0.1:1/guide")
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(AUDIT_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
