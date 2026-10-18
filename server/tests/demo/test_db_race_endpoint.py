"""The race endpoint over the REAL dev PostgreSQL.

``GET /api/demo/db/race`` must produce the two final states
deterministically, twice in a row: the unlocked run loses an update
(both transactions write the SAME slot number), the locked run
serializes on SELECT … FOR UPDATE (distinct consecutive slots), and the
demo leaves the database at its seed state — repeat calls are stable,
never flaky (the interleave is barrier-ordered awaits, not sleeps).
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

RACE_PATH = "/api/demo/db/race"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def _slots(run: dict) -> list[int]:
    import re

    numbers = []
    for slot in run["finalSlots"]:
        match = re.search(r"slot #(\d+)", slot["body"])
        assert match is not None
        numbers.append(int(match.group(1)))
    return numbers


def test_the_unlocked_run_loses_an_update(pg_client: TestClient) -> None:
    body = pg_client.get(RACE_PATH).json()
    unlocked = body["unlocked"]
    assert unlocked["mode"] == "read-modify-write"
    slots = _slots(unlocked)
    assert len(slots) == 2
    assert slots[0] == slots[1]  # both computed from the same stale read
    assert "LOST UPDATE" in unlocked["verdict"]
    assert baseline_slots_covered(body, unlocked)


def baseline_slots_covered(body: dict, run: dict) -> bool:
    """Both runs raced over the seeded first post and its baseline."""
    assert body["baselineComments"] >= 1
    assert body["postTitle"] == "Designing URLs people can read"
    return True


def test_the_locked_run_serializes_on_the_row_lock(pg_client: TestClient) -> None:
    body = pg_client.get(RACE_PATH).json()
    locked = body["locked"]
    assert locked["mode"] == "select-for-update"
    slots = _slots(locked)
    assert len(slots) == 2
    assert slots[1] == slots[0] + 1  # the second computed from a FRESH read
    assert "SERIALIZED" in locked["verdict"]
    timeline = "\n".join(locked["timeline"])
    assert "FOR UPDATE" in timeline
    assert "BLOCKS" in timeline


def test_both_runs_leave_the_database_at_the_seed_state(pg_client: TestClient) -> None:
    """Run the demo twice: identical, stable evidence — no flakes, no residue."""
    first = pg_client.get(RACE_PATH).json()
    second = pg_client.get(RACE_PATH).json()
    assert _slots(first["unlocked"]) == _slots(second["unlocked"])
    assert _slots(first["locked"]) == _slots(second["locked"])
    assert len(second["unlocked"]["finalSlots"]) == 2  # no accumulation


def test_unreachable_postgresql_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_DATABASE_URL", "postgresql+asyncpg://postgres:guide@127.0.0.1:1/guide")
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(RACE_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
