"""The shared demo-reset endpoint (Phase 12, area ``demo``): one POST, honest rows.

Pins the wire contract (POST /api/demo/reset): every demo state returns
to its baseline through the reset path it already owns, and the response
is a per-area report where every row carries the REAL result of this
request's action — counts and key names from the call that just ran.
The full round runs against the REAL dev-stack Redis (the playground's
posture): mutate every participating area through its public API, POST
the reset, then prove each baseline through the same API. The jobs
baseline is proven worker-independently by design: the live arq worker
is an independent writer to the comparison ledger (its queued half can
land after the reset), so the proof is that nothing pre-reset survives —
never "the ledger is empty right now". Unreachable Redis (the
deterministic offline fixture) degrades ONLY the redis-backed rows — the
in-process areas still reset — and the openapi declaration plus the
405-through-the-envelope shape are pinned with the plain client.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis_url import COMPOSE_REDIS_URL

from guide.core.config import get_config
from guide.core.errors import AppError, FailureKind
from guide.domain.demos.demo_reset import (
    NOT_RESET_AREAS,
    DemoResetService,
    ResetParticipant,
)
from guide.main import create_app

RESET_PATH = "/api/demo/reset"
SCENARIO_PATH = "/api/demo/scenario"
UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1"

AREA_ORDER = [
    "scenario",
    "posts",
    "caching",
    "scaling",
    "jobs",
    "security-pii",
    "observability",
]
NOT_RESET_ORDER = ["postgres", "mongo", "redis-streams"]

SUBJECT = "cust-2f9a41"
MINT_PATH = "/api/demo/auth/jwt/mint"


@pytest.fixture
def redis_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """App wired to the REAL dev-stack Redis — the redis-backed rows really run."""
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def offline_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """App wired to an unreachable Redis — deterministic degradation, fast."""
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def _rows(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The reset rows keyed by area."""
    return {row["area"]: row for row in body["reset"]}


def _bearer(client: TestClient, username: str) -> dict[str, str]:
    minted = client.post(MINT_PATH, json={"username": username, "scopes": ["*"]})
    assert minted.status_code == 200
    return {"Authorization": f"Bearer {minted.json()['token']}"}


def test_the_full_round_returns_every_area_to_baseline(
    redis_client: TestClient,
) -> None:
    # Mutate every participating area through its public API.
    patched = redis_client.patch(
        SCENARIO_PATH, json={"dataMode": "live", "injectFailure": "error"}
    )
    assert patched.status_code == 200

    created = redis_client.post(
        "/api/posts",
        json={
            "title": "A reset round post",
            "body": "Created only to be discarded by the shared reset.",
            "author": "grace",
            "tags": ["api"],
            "status": "published",
        },
    )
    assert created.status_code == 201
    created_slug = created.json()["id"]

    assert redis_client.get("/api/demo/scaling/stateless").status_code == 200
    assert redis_client.post("/api/demo/jobs/compare").status_code == 201
    comparison = redis_client.get("/api/demo/jobs/compare").json()
    assert len(comparison["runs"]) >= 1

    erase_path = f"/api/demo/security/pii/subjects/{SUBJECT}/erase"
    assert (
        redis_client.post(erase_path, headers=_bearer(redis_client, "ada")).status_code
        == 200
    )

    filled = redis_client.get("/api/demo/caching/posts")
    assert filled.headers["x-cache"] == "miss"  # the fill that puts the key there

    viewer_before = redis_client.get("/api/demo/obs/viewer").json()
    last_sequence = max(event["sequence"] for event in viewer_before["events"])

    # The reset itself.
    response = redis_client.post(RESET_PATH)
    assert response.status_code == 200
    body = response.json()
    assert [row["area"] for row in body["reset"]] == AREA_ORDER
    assert all(row["outcome"] == "reset" for row in body["reset"])
    assert all(row["detail"] for row in body["reset"])

    rows = _rows(body)
    assert "dataMode=fake" in rows["scenario"]["detail"]
    assert "13 posts discarded" in rows["posts"]["detail"]
    assert rows["caching"]["detail"].startswith("cache entry ")
    assert "deleted" in rows["caching"]["detail"]
    assert "guide_demo:scaling:shared deleted" in rows["scaling"]["detail"]
    assert "demo entries cleared" in rows["jobs"]["detail"]
    assert "3 synthetic customers" in rows["security-pii"]["detail"]
    assert "log ring cleared" in rows["observability"]["detail"]

    # Every baseline, proven through the same public APIs.
    assert redis_client.get(SCENARIO_PATH).json() == {
        "dataMode": "fake",
        "injectFailure": "none",
    }
    listing = redis_client.get("/api/posts", params={"limit": 1})
    assert listing.headers["x-total-count"] == "12"
    assert redis_client.get(f"/api/posts/{created_slug}").status_code == 404
    assert redis_client.get("/api/demo/caching/posts").headers["x-cache"] == "miss"

    # The live arq worker is an independent writer to the comparison ledger
    # — its queued half of the comparison can land after the reset (exactly
    # what the demo teaches), so "empty right now" races it. The
    # worker-immune baseline proof: nothing that existed BEFORE the reset
    # survives. Only the worker writes "queued" rows; the in-process row
    # (written before the reset returned) is gone, so any row still here
    # must be a fresh worker delivery.
    comparison_after = redis_client.get("/api/demo/jobs/compare").json()["runs"]
    assert all(run["side"] == "queued" for run in comparison_after)
    assert redis_client.get(f"/api/demo/security/pii/subjects/{SUBJECT}").status_code == 200

    # The ring clear is real: every displayed event was captured AFTER it.
    viewer_after = redis_client.get("/api/demo/obs/viewer").json()
    assert viewer_after["events"]
    assert min(event["sequence"] for event in viewer_after["events"]) > last_sequence


def test_the_not_reset_rows_name_the_deliberate_scope(
    redis_client: TestClient,
) -> None:
    body = redis_client.post(RESET_PATH).json()
    assert [row["area"] for row in body["notReset"]] == NOT_RESET_ORDER
    assert all(row["reason"] for row in body["notReset"])
    assert body["detail"]


def test_a_second_immediate_reset_reports_real_absences(
    redis_client: TestClient,
) -> None:
    created = redis_client.post(
        "/api/posts",
        json={
            "title": "Another reset round post",
            "body": "Discarded twice over.",
            "author": "alan",
            "tags": ["api"],
            "status": "published",
        },
    )
    assert created.status_code == 201
    assert redis_client.get("/api/demo/scaling/stateless").status_code == 200

    first = _rows(redis_client.post(RESET_PATH).json())
    assert "13 posts discarded" in first["posts"]["detail"]
    assert first["scaling"]["detail"] == (
        "shared counter key guide_demo:scaling:shared deleted"
    )

    # Nothing recreated the key between the two resets — the second row
    # says so, which is the proof the first deletion really happened.
    second = _rows(redis_client.post(RESET_PATH).json())
    assert "12 posts discarded" in second["posts"]["detail"]
    assert second["scaling"]["detail"] == (
        "shared counter key guide_demo:scaling:shared already absent"
    )


def test_offline_redis_degrades_only_the_redis_backed_rows(
    offline_client: TestClient,
) -> None:
    assert (
        offline_client.patch(
            SCENARIO_PATH, json={"dataMode": "live", "injectFailure": "error"}
        ).status_code
        == 200
    )
    response = offline_client.post(RESET_PATH)
    assert response.status_code == 200

    rows = _rows(response.json())
    for area in ("scenario", "posts", "security-pii", "observability"):
        assert rows[area]["outcome"] == "reset", area
    for area in ("caching", "scaling", "jobs"):
        assert rows[area]["outcome"] == "degraded", area
        assert "service_unavailable" in rows[area]["detail"]

    # The in-process areas still reset — one unreachable store costs only
    # the areas that owe it something.
    assert offline_client.get(SCENARIO_PATH).json() == {
        "dataMode": "fake",
        "injectFailure": "none",
    }


async def test_the_service_degrades_app_errors_and_propagates_bugs() -> None:
    async def _ok() -> str:
        return "the honest result"

    async def _down() -> str:
        raise AppError(FailureKind.SERVICE_UNAVAILABLE, "Redis is unreachable")

    async def _buggy() -> str:
        raise RuntimeError("a bug, not a degraded demo")

    degraded = DemoResetService(
        [
            ResetParticipant("ok-area", "Ok area", _ok),
            ResetParticipant("down-area", "Down area", _down),
        ]
    )
    report = await degraded.run()
    assert [(row.area, row.outcome) for row in report.reset] == [
        ("ok-area", "reset"),
        ("down-area", "degraded"),
    ]
    assert report.reset[0].detail == "the honest result"
    assert "Redis is unreachable" in report.reset[1].detail
    assert [row.area for row in report.not_reset] == [row.area for row in NOT_RESET_AREAS]
    assert [row.area for row in report.not_reset] == ["postgres", "mongo", "redis-streams"]

    buggy = DemoResetService([ResetParticipant("bug", "Bug", _buggy)])
    with pytest.raises(RuntimeError, match="a bug, not a degraded demo"):
        await buggy.run()


def test_a_buggy_participant_answers_the_500_envelope(
    app: FastAPI,
) -> None:
    async def _buggy() -> str:
        raise RuntimeError("participant bug")

    app.state.demo_reset_service = DemoResetService(
        [ResetParticipant("bug", "Bug", _buggy)]
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(RESET_PATH)
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal"
    assert error["requestId"] == response.headers["x-request-id"]


def test_route_shape_is_declared_and_wrong_methods_use_the_envelope(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()
    reset_spec = schema["paths"][RESET_PATH]
    assert list(reset_spec) == ["post"]
    ref = reset_spec["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert ref.endswith("ResetReport")

    # No GET twin and no silent 404: the wrong method answers 405 through
    # the shared envelope (the taxonomy's unnamed-4xx bucket), with the
    # request id round-tripped like every other error.
    denied = client.get(RESET_PATH)
    assert denied.status_code == 405
    error = denied.json()["error"]
    assert error["code"] == "not_found"
    assert error["requestId"] == denied.headers["x-request-id"]
