"""app.dependency_overrides: swapping providers without touching wiring.

The pattern the whole guide leans on for tests: handlers declare what they
need via ``Depends``; a test replaces the PROVIDER in the app's override
table and every route that depends on it now receives the fake — no
monkeypatching, no test-only constructor flags. These tests exercise both
halves the guide's demos expose: the scenario store (classic state swap)
and the span log (which the yield dependency itself resolves through a
sub-dependency — overriding it re-points the whole instrument).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guide.core.scenario import ScenarioState, ScenarioStore, get_scenario_store
from guide.presentation.dependencies.request_span import SpanLog, get_span_log


@pytest.fixture
def overrides(app: FastAPI) -> FastAPI:
    """The fresh per-test app, with the override table cleaned afterwards."""
    yield app
    app.dependency_overrides.clear()


def test_scenario_store_override_swaps_the_wired_store(
    overrides: FastAPI, client: TestClient
) -> None:
    fake = ScenarioStore(initial=ScenarioState(data_mode="live"))
    overrides.dependency_overrides[get_scenario_store] = lambda: fake

    body = client.get("/api/demo/scenario").json()
    assert body["dataMode"] == "live"  # the override's state, not the app's

    client.patch("/api/demo/scenario", json={"injectFailure": "error"})
    assert fake.get() == ScenarioState(
        data_mode="live", inject_failure="error"
    )  # PATCH wrote through the override too


def test_span_log_override_re_points_the_whole_instrument(
    overrides: FastAPI, client: TestClient
) -> None:
    fake = SpanLog(capacity=8)
    overrides.dependency_overrides[get_span_log] = lambda: fake

    # The log endpoint reads the fake (its capacity gives it away)…
    log = client.get("/api/demo/dep/lifecycle/log").json()
    assert log["capacity"] == 8
    assert log["events"] == []

    # …and the lifecycle endpoint writes through it, because the yield
    # dependency resolves the log as its own sub-dependency.
    client.get("/api/demo/dep/lifecycle")
    beats = [event["event"] for event in client.get("/api/demo/dep/lifecycle/log").json()["events"]]
    assert beats == ["setup", "handler", "response", "teardown"]
