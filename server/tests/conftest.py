"""Shared fixtures: a fresh app per test and a sync TestClient over it."""

import os
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guide.core.config import get_config
from guide.core.request_context import reset_request_context
from guide.main import create_app


@pytest.fixture(autouse=True)
def _isolated_request_context() -> Iterator[None]:
    """Request-id contextvar isolation: cleared before and after every test.

    The middleware resets its own token per request, but the unhandled-
    exception path intentionally leaves the outermost handler reading the
    scope mirror — this guarantees no ambient id leaks between tests.
    """
    reset_request_context()
    yield
    reset_request_context()


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    """Fresh application per test.

    Neutralizes every FDG_* env var (tests never depend on the host
    environment) and clears the config cache around each app build.
    """

    for name in [key for key in os.environ if key.startswith("FDG_")]:
        monkeypatch.delenv(name)
    get_config.cache_clear()
    yield create_app()
    get_config.cache_clear()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Sync HTTP client bound to the per-test app."""
    return TestClient(app)
