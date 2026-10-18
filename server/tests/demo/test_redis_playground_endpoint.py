"""The redis playground endpoint over the REAL dev Redis.

``GET /api/demo/redis/playground`` must serve the scripted walk with real
results (five structures, the honest TTL proof, the real pub/sub round-trip),
weave the caller's tag into keys and values, validate the tag at the edge,
and degrade to the ``service_unavailable`` envelope when Redis is
unreachable — while the app itself keeps booting and serving content, which
the boot-without-redis test below proves at the wiring level.
"""

import pytest
from fastapi.testclient import TestClient
from redis_url import COMPOSE_REDIS_URL

from guide.core.config import get_config
from guide.main import create_app

REDIS_PLAYGROUND_PATH = "/api/demo/redis/playground"

UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1"


@pytest.fixture
def redis_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_the_playground_serves_real_results(redis_client: TestClient) -> None:
    body = redis_client.get(REDIS_PLAYGROUND_PATH).json()
    assert body["namespace"] == "guide_demo:redis:*"
    assert [s["kind"] for s in body["structures"]] == ["string", "hash", "list", "set", "zset"]
    # The counter: SET 1, two atomic INCRs, GET 3 — all real.
    assert [v["value"] for v in body["structures"][0]["values"]] == ["1", "3"]
    # The TTL proof: the live clock, then the absence after the bounded wait.
    assert body["ttl"]["absentAfterExpiry"] is True
    assert 1 <= body["ttl"]["ttlFirstRead"] <= body["ttl"]["ttlSeconds"]
    # The pub/sub round-trip: both sides, one message.
    assert body["pubsub"]["matched"] is True
    assert body["pubsub"]["receivedPayload"] == body["pubsub"]["payload"]
    assert body["pubsub"]["receivers"] == 1
    assert "INCR" in body["reasoning"]


def test_the_tag_is_woven_into_keys_and_values(redis_client: TestClient) -> None:
    body = redis_client.get(REDIS_PLAYGROUND_PATH, params={"tag": "tour"}).json()
    assert body["tag"] == "tour"
    assert all(":tour:" in s["key"] for s in body["structures"])
    hash_values = {v["label"]: v["value"] for v in body["structures"][1]["values"]}
    assert hash_values["tag"] == "tour"
    assert body["pubsub"]["channel"] == "guide_demo:redis:tour:events"


def test_tag_is_validated_as_a_kebab_slug(redis_client: TestClient) -> None:
    assert redis_client.get(REDIS_PLAYGROUND_PATH, params={"tag": "Not A Tag"}).status_code == 422
    assert redis_client.get(REDIS_PLAYGROUND_PATH, params={"tag": "x" * 25}).status_code == 422
    assert redis_client.get(REDIS_PLAYGROUND_PATH, params={"tag": ""}).status_code == 422


def test_unreachable_redis_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.get(REDIS_PLAYGROUND_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_the_app_boots_and_serves_with_redis_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The optional-service discipline, proven at the wiring level: an
    unreachable redis URL never stops the app from booting or serving —
    only the redis demo degrades."""
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        content = client.get("/api/content")
        assert content.status_code == 200
        assert len(content.json()["topics"]) >= 20
        degraded = client.get(REDIS_PLAYGROUND_PATH)
        assert degraded.status_code == 503
        assert degraded.json()["error"]["code"] == "service_unavailable"
