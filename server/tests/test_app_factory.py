"""create_app() wiring: title/version, independence, routes, JSON logging."""

import json

import pytest
import structlog
from fastapi import FastAPI

import guide
from guide.main import APP_TITLE, create_app


def test_factory_wires_title_and_version() -> None:
    app = create_app()
    assert app.title == APP_TITLE
    assert app.version == guide.__version__


def test_factory_returns_independent_apps() -> None:
    first = create_app()
    second = create_app()
    assert first is not second
    assert first.routes is not second.routes
    assert first.dependency_overrides is not second.dependency_overrides
    # Both wire the same routes, resolved through each app's own routing table.
    assert first.url_path_for("read_health") == second.url_path_for("read_health")


def test_health_route_registered(app: FastAPI) -> None:
    """Route presence via the public resolver, not app.routes internals
    (include_router composes routers since FastAPI 0.143)."""

    assert app.url_path_for("read_health") == "/api/health"


def test_module_level_app_exists() -> None:
    from guide.main import app

    assert isinstance(app, FastAPI)


def test_create_app_applies_json_logging(
    app: FastAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    structlog.get_logger().info("factory-check")
    record = json.loads(capsys.readouterr().out)
    assert record["event"] == "factory-check"
    assert record["level"] == "info"
    assert "timestamp" in record
