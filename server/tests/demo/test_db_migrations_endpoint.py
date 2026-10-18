"""The migrations-rehearsal endpoint over the REAL dev PostgreSQL.

``GET /api/demo/db/migrations`` must prove transactional DDL atomicity:
the failing run's mid-sequence failure rolls back CREATE TABLE and
INSERT with it (the verification finds no table), the succeeding run
commits (table present, one row), and the whole demo repeats — calling
it twice changes nothing (the scratch table is dropped after the proof).
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

MIGRATIONS_PATH = "/api/demo/db/migrations"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_the_failing_run_rolls_back_everything(pg_client: TestClient) -> None:
    body = pg_client.get(MIGRATIONS_PATH).json()
    failing = body["failing"]
    assert failing["scratchTable"] == "migration_lab_scratch"
    outcomes = [step["outcome"] for step in failing["steps"]]
    assert outcomes[0] == "applied"
    assert outcomes[1] == "applied"
    assert outcomes[2].startswith("failed:")
    assert "contains null values" in failing["failure"]
    # The proof: the earlier steps did NOT survive the failed third one.
    assert failing["committed"] is False
    assert failing["tableExistsAfter"] is False
    assert "rowCountAfter" not in failing  # exclude_none drops the None


def test_the_succeeding_run_commits_and_is_verified(pg_client: TestClient) -> None:
    body = pg_client.get(MIGRATIONS_PATH).json()
    succeeding = body["succeeding"]
    assert all(step["outcome"] == "applied" for step in succeeding["steps"])
    assert succeeding["committed"] is True
    assert succeeding["tableExistsAfter"] is True
    assert succeeding["rowCountAfter"] == 1
    assert "DEFAULT 0" in succeeding["steps"][2]["sql"]


def test_the_demo_is_idempotent_across_calls(pg_client: TestClient) -> None:
    first = pg_client.get(MIGRATIONS_PATH).json()
    second = pg_client.get(MIGRATIONS_PATH).json()
    assert first["failing"]["tableExistsAfter"] is False
    assert second["failing"]["tableExistsAfter"] is False
    assert second["succeeding"]["rowCountAfter"] == 1
    assert "drops migration_lab_scratch again" in second["cleanupNote"]


def test_unreachable_postgresql_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_DATABASE_URL", "postgresql+asyncpg://postgres:guide@127.0.0.1:1/guide")
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(MIGRATIONS_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
