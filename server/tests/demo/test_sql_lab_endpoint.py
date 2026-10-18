"""The sql-lab endpoint over the REAL dev PostgreSQL.

``GET /api/demo/db/sql-lab?exhibit=ranked|window|thread`` executes the
hand-written exhibits against the seeded data: the ranked exhibit
numbers each author's posts (ROW_NUMBER per partition) and ranks by
comment count; the window exhibit's last running total equals the whole
table's comment count; the recursive thread exhibit walks the
most-commented post's five comments in id order with depth 1..5. An
unknown exhibit is refused at the edge (422).
"""

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL

from guide.core.config import get_config
from guide.main import create_app

LAB_PATH = "/api/demo/db/sql-lab"


@pytest.fixture
def pg_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_default_exhibit_is_ranked_and_the_shapes_are_real(pg_client: TestClient) -> None:
    body = pg_client.get(LAB_PATH).json()
    assert body["exhibit"] == "ranked"
    assert [card["id"] for card in body["exhibits"]] == ["ranked", "window", "thread"]
    assert body["columns"] == [
        "author", "post_id", "title", "comment_count", "nth_post", "by_comments",
    ]
    assert body["rowCount"] == 12  # every seeded post, one row each
    # ROW_NUMBER partitions by author: each author's posts number 1..n.
    by_author: dict[str, list[str]] = {}
    for row in body["rows"]:
        by_author.setdefault(row["author"], []).append(row["nth_post"])
    for author, numbers in by_author.items():
        assert numbers == [str(n) for n in range(1, len(numbers) + 1)], author
    # The most-commented post (5 comments) holds global rank 1.
    top = next(row for row in body["rows"] if row["comment_count"] == "5")
    assert top["by_comments"] == "1"


def test_window_exhibit_running_total_converges(pg_client: TestClient) -> None:
    body = pg_client.get(LAB_PATH, params={"exhibit": "window"}).json()
    assert body["exhibit"] == "window"
    rows = body["rows"]
    assert len(rows) == 12
    total = sum(int(row["comments"]) for row in rows)
    assert int(rows[-1]["running_comments"]) == total  # the running total lands
    # Monotone: the running total never decreases along the timeline.
    running = [int(row["running_comments"]) for row in rows]
    assert running == sorted(running)


def test_thread_exhibit_walks_the_comment_thread(pg_client: TestClient) -> None:
    body = pg_client.get(LAB_PATH, params={"exhibit": "thread"}).json()
    assert body["exhibit"] == "thread"
    rows = body["rows"]
    assert [row["depth"] for row in rows] == [str(n) for n in range(1, len(rows) + 1)]
    assert len(rows) == 5  # the seeded status-codes thread
    assert "WITH RECURSIVE" in body["sql"]


def test_unknown_exhibit_is_refused_at_the_edge(pg_client: TestClient) -> None:
    response = pg_client.get(LAB_PATH, params={"exhibit": "pivot"})
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
    response = client.get(LAB_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
