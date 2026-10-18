"""The search endpoint over the REAL dev PostgreSQL (and migration 0002).

``GET /api/demo/db/search?q=`` runs the ranked full-text query over the
generated tsvector column: the parsed query shows stemming, ts_rank
orders the matches strictly, the indexed plan is a Bitmap Index Scan on
the GIN index while the naive plan recomputes to_tsvector per row, a
no-hit query is data (not an error), and injection-shaped input
dissolves into lexemes.
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

SEARCH_PATH = "/api/demo/db/search"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_default_query_ranks_matches_over_the_generated_column(pg_client: TestClient) -> None:
    body = pg_client.get(SEARCH_PATH).json()
    assert body["query"] == "error envelope"
    # plainto_tsquery parsed AND stemmed lexemes — never raw substrings.
    assert body["parsedQuery"] == "'error' & 'envelop'"
    assert body["matchCount"] == 3
    ranks = [match["rank"] for match in body["matches"]]
    assert ranks == sorted(ranks, reverse=True)  # ranked, best first
    assert body["matches"][0]["title"] == "The envelope is the error model"
    assert "<b>envelope</b>" in body["matches"][0]["headline"]


def test_both_explain_plans_are_the_real_ones(pg_client: TestClient) -> None:
    body = pg_client.get(SEARCH_PATH, params={"q": "error envelope"}).json()
    indexed = "\n".join(body["indexedPlan"])
    naive = "\n".join(body["naivePlan"])
    assert "Bitmap Index Scan on ix_posts_search_vector" in indexed
    assert "Recheck Cond" in indexed
    assert "Seq Scan on posts" in naive
    assert "to_tsvector" in naive  # recomputed per row — the no-index cost
    # The honesty note about SET LOCAL is part of the payload.
    assert "enable_seqscan" in body["planNote"]


def test_a_no_hit_query_is_data_not_an_error(pg_client: TestClient) -> None:
    body = pg_client.get(SEARCH_PATH, params={"q": "kubernetes helm chart"}).json()
    assert body["matchCount"] == 0
    assert body["matches"] == []
    assert "no post matches" in body["reasoning"]


def test_injection_shaped_input_dissolves_into_lexemes(pg_client: TestClient) -> None:
    body = pg_client.get(SEARCH_PATH, params={"q": "'; DROP TABLE posts; --"}).json()
    assert body["matchCount"] == 0  # the payload became lexemes that match nothing
    assert "drop" in body["parsedQuery"].lower()


def test_overlong_query_is_refused_at_the_edge(pg_client: TestClient) -> None:
    response = pg_client.get(SEARCH_PATH, params={"q": "x" * 201})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
