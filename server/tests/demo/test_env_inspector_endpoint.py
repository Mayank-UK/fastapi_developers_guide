"""The env-inspector endpoint (topic 36, area ``env``): the real config panel.

Pins the wire contract (GET /api/demo/env): every AppConfig field appears
with its env-var name, type, effective value, and honestly-introspected
source; secret-bearing fields are REDACTED server-side — the hard rule this
demo exists to teach is asserted here against the FULL serialized payload,
with live sentinel secrets planted in the environment so the proof is real
and not a tautology over defaults.
"""

import json
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guide.core.config import AppConfig, get_config
from guide.core.scenario import ScenarioState
from guide.domain.demos.env_inspector import build_env_inspector_payload
from guide.main import create_app

PANEL_PATH = "/api/demo/env"

LIVE_JWT_SECRET = "live-jwt-sentinel-only-for-this-test-0123456789"
LIVE_SESSION_SECRET = "live-session-sentinel-only-for-this-test-0123456789"
"""Sentinels planted via the environment — asserting their absence proves the
redaction, because the values really were the process's live config."""


def row_by_name(body: dict[str, Any], name: str) -> dict[str, Any]:
    """The settings row whose field name matches (wire key ``name``)."""
    return next(row for row in body["settings"] if row["name"] == name)


def test_panel_serves_every_real_config_field(app: FastAPI, client: TestClient) -> None:
    response = client.get(PANEL_PATH)
    assert response.status_code == 200
    body = response.json()

    assert body["environment"] == "dev"  # neutralized env -> declared default
    assert body["envVar"] == "FDG_ENV"
    assert body["facts"] == {
        "envPrefix": "FDG_",
        "frozen": True,
        "cache": "one instance per process (get_config is lru_cache'd)",
    }
    names = [row["name"] for row in body["settings"]]
    assert names == [
        "env",
        "debug",
        "database_url",
        "redis_url",
        "mongo_url",
        "log_level",
        "jwt_secret",
        "session_secret",
    ]
    assert [row["envVar"] for row in body["settings"][:3]] == [
        "FDG_ENV",
        "FDG_DEBUG",
        "FDG_DATABASE_URL",
    ]
    assert body["sourceNote"]
    assert body["redactionNote"]


def test_live_secrets_appear_nowhere_in_the_full_serialized_panel(
    app: FastAPI, monkeypatch: Any
) -> None:
    monkeypatch.setenv("FDG_JWT_SECRET", LIVE_JWT_SECRET)
    monkeypatch.setenv("FDG_SESSION_SECRET", LIVE_SESSION_SECRET)
    get_config.cache_clear()
    sentinel_app = create_app()
    try:
        body = TestClient(sentinel_app).get(PANEL_PATH).json()

        serialized = json.dumps(body)
        assert LIVE_JWT_SECRET not in serialized
        assert LIVE_SESSION_SECRET not in serialized

        jwt_row = row_by_name(body, "jwt_secret")
        assert jwt_row["value"] == "redacted"
        assert jwt_row["shapeHint"] == f"{len(LIVE_JWT_SECRET)} chars, hidden"
        assert jwt_row["secret"] is True
        assert jwt_row["redacted"] is True
        session_row = row_by_name(body, "session_secret")
        assert session_row["value"] == "redacted"
        assert session_row["shapeHint"] == f"{len(LIVE_SESSION_SECRET)} chars, hidden"
    finally:
        get_config.cache_clear()


def test_source_attribution_is_real_introspection_not_a_guess(
    app: FastAPI, monkeypatch: Any
) -> None:
    # The fixture app (FDG_* neutralized): every field fell back to default.
    neutral = TestClient(app).get(PANEL_PATH).json()
    assert all(row["source"] == "default" for row in neutral["settings"])

    # One env var set before a fresh app build: exactly that row flips to env.
    monkeypatch.setenv("FDG_LOG_LEVEL", "debug")
    get_config.cache_clear()
    fresh_app = create_app()
    try:
        body = TestClient(fresh_app).get(PANEL_PATH).json()
        log_row = row_by_name(body, "log_level")
        assert log_row["source"] == "env"
        assert log_row["value"] == "debug"
        assert row_by_name(body, "debug")["source"] == "default"
    finally:
        get_config.cache_clear()


def test_flags_subpanel_tracks_the_live_scenario_state(
    app: FastAPI, client: TestClient
) -> None:
    flags = client.get(PANEL_PATH).json()["flags"]
    assert flags["getEndpoint"] == "/api/demo/scenario"
    assert flags["patchEndpoint"] == "/api/demo/scenario"
    assert flags["dataMode"] == "fake"
    assert flags["injectFailure"] == "none"

    patched = client.patch(
        "/api/demo/scenario", json={"dataMode": "live"}
    )
    assert patched.status_code == 200
    flags = client.get(PANEL_PATH).json()["flags"]
    assert flags["dataMode"] == "live"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][PANEL_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("EnvInspectorPanel")


def test_the_pure_builder_redacts_and_attributes_without_an_app() -> None:
    payload = build_env_inspector_payload(
        AppConfig(debug=True, jwt_secret=LIVE_JWT_SECRET),
        ScenarioState(data_mode="live"),
        env_provided={"env": "prod"},
    )
    assert payload.environment == "dev"  # the instance's own frozen value
    assert payload.settings[0].name == "env"
    assert payload.settings[0].source == "env"
    assert payload.settings[1].value == "True"  # str(True), honestly stringified
    assert payload.settings[6].value == "redacted"
    assert payload.settings[6].shape_hint == f"{len(LIVE_JWT_SECRET)} chars, hidden"
    assert payload.settings[7].secret is True
    assert payload.flags.data_mode == "live"
    assert "redacted" in payload.redaction_note
