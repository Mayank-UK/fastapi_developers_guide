"""The mongo-console endpoint over the REAL dev MongoDB.

``GET /api/demo/db/mongo-console`` must serve the scripted console with
real results (seed idempotence, the boundary refusal, find with
projection + sort, the COLLSCAN→IXSCAN exhibit, the TTL index) and
degrade to the ``service_unavailable`` envelope when MongoDB is
unreachable — while the app itself keeps booting and serving content,
which the boot-without-mongo test below proves at the wiring level.
"""

import pytest
from fastapi.testclient import TestClient
from mongo_url import COMPOSE_MONGO_URL

from guide.core.config import get_config
from guide.main import create_app

MONGO_CONSOLE_PATH = "/api/demo/db/mongo-console"

UNREACHABLE_MONGO_URL = "mongodb://127.0.0.1:1"


@pytest.fixture
def mongo_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_MONGO_URL", COMPOSE_MONGO_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_the_console_serves_real_results(mongo_client: TestClient) -> None:
    body = mongo_client.get(MONGO_CONSOLE_PATH).json()
    assert body["database"] == "guide_demo"
    assert [op["op"] for op in body["operations"]] == [
        "insert",
        "find",
        "update",
        "count",
        "delete",
    ]
    # The boundary: three refusals, then the accepted insert's real id.
    assert len(body["refusal"]["errors"]) == 3
    assert body["operations"][0]["outcome"].startswith("acknowledged — insertedId")
    # The find: default tag "indexes", projection held to four fields, newest first.
    find = body["operations"][1]
    assert [doc["key"] for doc in find["documents"]] == [
        "mongo-note-ttl",
        "mongo-note-indexes",
        "mongo-note-embedding",
    ]
    assert all(set(doc) == {"key", "title", "author", "created_at"} for doc in find["documents"])
    # The exhibits: COLLSCAN → IXSCAN with real examined counts, a real TTL index.
    collscan, ixscan = body["indexShowcase"]["explains"]
    assert (collscan["stage"], collscan["docsExamined"]) == ("COLLSCAN", 8)
    assert (ixscan["stage"], ixscan["indexName"], ixscan["keysExamined"]) == (
        "IXSCAN",
        "title_1",
        1,
    )
    assert body["ttlShowcase"]["expireAfterSeconds"] == 10
    assert "IXSCAN" in body["reasoning"]


def test_the_demo_repeats_identically(mongo_client: TestClient) -> None:
    """Seed is keyed, the demo document is deleted at the end — repeats agree."""
    first = mongo_client.get(MONGO_CONSOLE_PATH).json()
    second = mongo_client.get(MONGO_CONSOLE_PATH).json()
    assert first["seed"]["totalAfter"] == second["seed"]["totalAfter"] == 6
    assert [doc["key"] for doc in first["operations"][1]["documents"]] == [
        doc["key"] for doc in second["operations"][1]["documents"]
    ]
    assert second["operations"][4]["outcome"] == "deletedCount 1"


def test_unknown_tag_is_an_honest_empty(mongo_client: TestClient) -> None:
    body = mongo_client.get(MONGO_CONSOLE_PATH, params={"tag": "no-such-tag"}).json()
    find, count = body["operations"][1], body["operations"][3]
    assert find["documents"] == []
    assert "empty cursor" in find["outcome"]
    assert count["outcome"] == "0 document(s)"


def test_tag_is_validated_as_a_kebab_slug(mongo_client: TestClient) -> None:
    assert mongo_client.get(MONGO_CONSOLE_PATH, params={"tag": "Not A Tag"}).status_code == 422
    assert mongo_client.get(MONGO_CONSOLE_PATH, params={"tag": "x" * 41}).status_code == 422
    assert mongo_client.get(MONGO_CONSOLE_PATH, params={"tag": ""}).status_code == 422


def test_unreachable_mongodb_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_MONGO_URL", UNREACHABLE_MONGO_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(MONGO_CONSOLE_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_the_app_boots_and_serves_with_mongo_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The optional-service discipline, proven at the wiring level: an
    unreachable mongo URL never stops the app from booting or serving —
    only the mongo demo degrades."""
    monkeypatch.setenv("FDG_MONGO_URL", UNREACHABLE_MONGO_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        content = client.get("/api/content")
        assert content.status_code == 200
        assert len(content.json()["topics"]) >= 19
        degraded = client.get(MONGO_CONSOLE_PATH)
        assert degraded.status_code == 503
        assert degraded.json()["error"]["code"] == "service_unavailable"
