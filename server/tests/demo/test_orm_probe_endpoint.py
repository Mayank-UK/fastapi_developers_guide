"""The orm-probe endpoint over the REAL dev PostgreSQL.

``GET /api/demo/db/orm-probe`` must report the three loading strategies
with the counts the engine actually emitted (lazy shows the N+1 shape,
selectinload batches it away, joinedload collapses it to one statement),
the identity-map proof (two gets, ONE SELECT, same object), and the
dirty-checking proof (one mutated field → exactly one UPDATE, rolled
back so repeats are identical). Counts are pinned only where they are
deterministic: five seeded published posts touch three distinct authors
— the audit demo's status toggle affects post seven and later, never
the first five.
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

ORM_PROBE_PATH = "/api/demo/db/orm-probe"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def _strategies(body: dict) -> dict[str, dict]:
    return {card["strategy"]: card for card in body["strategies"]}


def test_lazy_shows_the_n_plus_one_shape(pg_client: TestClient) -> None:
    body = pg_client.get(ORM_PROBE_PATH).json()
    lazy = _strategies(body)["lazy"]
    # 1 posts + 3 distinct authors (identity map dedupes repeats) + 5 comment loads.
    assert lazy["sqlCount"] == 9
    assert sum(1 for s in lazy["statements"] if s.lstrip().upper().startswith("SELECT")) == 9
    assert lazy["commentTotal"] == 11  # the first five seeded posts' comments


def test_selectinload_batches_and_joinedload_collapses(pg_client: TestClient) -> None:
    body = pg_client.get(ORM_PROBE_PATH).json()
    strategies = _strategies(body)
    assert strategies["selectinload"]["sqlCount"] == 3  # posts + authors IN + comments IN
    assert "IN" in strategies["selectinload"]["statements"][1].upper()
    assert strategies["joinedload"]["sqlCount"] == 1
    joined = strategies["joinedload"]["statements"][0].upper()
    assert "JOIN AUTHORS" in joined and "JOIN COMMENTS" in joined


def test_all_strategies_return_identical_results(pg_client: TestClient) -> None:
    body = pg_client.get(ORM_PROBE_PATH).json()
    assert body["resultsMatch"] is True
    cards = body["strategies"]
    assert {card["authorCount"] for card in cards} == {5}
    assert {card["commentTotal"] for card in cards} == {11}
    assert body["postCount"] == 5
    assert body["firstPostTitle"] == "Designing URLs people can read"


def test_identity_map_proof_two_gets_one_select(pg_client: TestClient) -> None:
    identity = pg_client.get(ORM_PROBE_PATH).json()["identityMap"]
    assert identity["selectCount"] == 1
    assert identity["sameObject"] is True
    assert len(identity["statements"]) == 1


def test_dirty_check_proof_one_update_then_rollback(pg_client: TestClient) -> None:
    dirty = pg_client.get(ORM_PROBE_PATH).json()["dirtyCheck"]
    assert dirty["updateCount"] == 1
    assert dirty["committed"] is False
    assert dirty["before"] != dirty["after"]
    # The version counter migration 0003 added rides in the WHERE clause.
    assert "version" in dirty["updateSql"]


def test_the_demo_repeats_identically(pg_client: TestClient) -> None:
    """The proofs roll back and clean up: a second run answers the same."""
    first = pg_client.get(ORM_PROBE_PATH).json()
    second = pg_client.get(ORM_PROBE_PATH).json()
    assert [c["sqlCount"] for c in first["strategies"]] == [
        c["sqlCount"] for c in second["strategies"]
    ]
    assert first["identityMap"]["selectCount"] == second["identityMap"]["selectCount"]
    assert first["dirtyCheck"]["updateCount"] == second["dirtyCheck"]["updateCount"]
    assert first["dirtyCheck"]["before"] == second["dirtyCheck"]["before"]


def test_post_count_parameter_clamps_are_validated(pg_client: TestClient) -> None:
    assert pg_client.get(ORM_PROBE_PATH, params={"posts": 0}).status_code == 422
    assert pg_client.get(ORM_PROBE_PATH, params={"posts": 10}).status_code == 422
    body = pg_client.get(ORM_PROBE_PATH, params={"posts": 2}).json()
    # Two published posts by one author: 1 + 1 author + 2 comment loads.
    assert {card["strategy"]: card["sqlCount"] for card in body["strategies"]} == {
        "lazy": 4,
        "joinedload": 1,
        "selectinload": 3,
    }


def test_unreachable_postgresql_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_DATABASE_URL", "postgresql+asyncpg://postgres:guide@127.0.0.1:1/guide")
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(ORM_PROBE_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
