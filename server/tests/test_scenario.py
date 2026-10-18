"""ScenarioStore + GET/PATCH /api/demo/scenario: defaults, partials, reset."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guide.core.errors import AppError, FailureKind
from guide.core.scenario import ScenarioPatch, ScenarioState, ScenarioStore
from guide.main import create_app

SCENARIO_PATH = "/api/demo/scenario"


def test_defaults_are_fake_and_none(client: TestClient) -> None:
    assert client.get(SCENARIO_PATH).json() == {"dataMode": "fake", "injectFailure": "none"}


def test_patch_updates_only_given_fields(client: TestClient) -> None:
    first = client.patch(SCENARIO_PATH, json={"dataMode": "live"})
    assert first.json() == {"dataMode": "live", "injectFailure": "none"}

    second = client.patch(SCENARIO_PATH, json={"injectFailure": "latency"})
    assert second.json() == {"dataMode": "live", "injectFailure": "latency"}


def test_patch_accepts_snake_case_keys_too(client: TestClient) -> None:
    response = client.patch(SCENARIO_PATH, json={"data_mode": "live"})
    assert response.json() == {"dataMode": "live", "injectFailure": "none"}


def test_invalid_enum_value_is_422_envelope(client: TestClient) -> None:
    response = client.patch(SCENARIO_PATH, json={"injectFailure": "bogus"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_store_reset_restores_initial_state() -> None:
    store = ScenarioStore(initial=ScenarioState(data_mode="live"))
    store.update(ScenarioPatch(inject_failure="error"))
    assert store.get().inject_failure == "error"

    store.reset()
    assert store.get() == ScenarioState(data_mode="live", inject_failure="none")


def test_store_defends_its_enums_against_untyped_callers() -> None:
    store = ScenarioStore()
    hostile = ScenarioPatch.model_construct(data_mode="staging")  # bypasses validation
    with pytest.raises(AppError) as excinfo:
        store.update(hostile)
    assert excinfo.value.kind is FailureKind.VALIDATION_FAILED


def test_scenario_state_is_per_app() -> None:
    first = TestClient(create_app())
    second = TestClient(create_app())

    first.patch(SCENARIO_PATH, json={"dataMode": "live"})
    assert second.get(SCENARIO_PATH).json() == {"dataMode": "fake", "injectFailure": "none"}


def test_scenario_store_wired_on_app_state(app: FastAPI) -> None:
    assert isinstance(app.state.scenario, ScenarioStore)
