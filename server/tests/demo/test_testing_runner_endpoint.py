"""The testing-runner endpoints: roster contract, real runs, the recursion guard.

The roster and boundary behavior pin cheaply; the run tests fire REAL
subprocess pytest rounds (the demo's whole point — the results below are
genuine, not composed). Two guards are proven here, not asserted on
faith: the roster can never name this file (checked against the live
roster), and a pytest started BY the runner skips this module on the
``FDG_TEST_RUNNER_CHILD`` marker — demonstrated by actually starting one.

The off-loop proof is this repo's first ASGI-transport async client test:
``httpx.AsyncClient`` over ``ASGITransport(app=app)`` drives the run
endpoint and a health probe concurrently on ONE event loop — if the
subprocess sat on the loop instead of a worker thread, the health probe
could not land mid-run, and the timing ratio below would collapse.
"""

import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Final

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guide.domain.demos.testing_runner import RUNNER_CHILD_ENV, slices

PANEL_PATH = "/api/demo/testing"
UNIT_PURE_RUN = "/api/demo/testing/run/unit-pure"
TESTCONTAINERS_RUN = "/api/demo/testing/run/testcontainers-skips"

SERVER_ROOT: Final = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    bool(os.environ.get(RUNNER_CHILD_ENV)),
    reason="runner-started pytest never re-reaches the runner's own tests (recursion guard)",
)


def test_the_roster_serves_four_curated_slices_and_the_client_recipe(client: TestClient) -> None:
    body = client.get(PANEL_PATH).json()
    assert [row["sliceId"] for row in body["slices"]] == [
        "unit-pure",
        "fixtures-testclient",
        "async-native",
        "testcontainers-skips",
    ]
    assert all(row["paths"] for row in body["slices"])
    assert body["clientRecipe"]["command"].startswith("docker exec")
    assert "npm test" in body["clientRecipe"]["command"]
    assert body["facts"]["guardEnv"] == RUNNER_CHILD_ENV
    assert body["facts"]["timeoutSeconds"] > 0
    assert "asyncio.to_thread" in body["facts"]["offLoop"]


def test_the_roster_cannot_name_the_runner_s_own_tests(client: TestClient) -> None:
    """Guard wall one, against the live roster: no path reaches this file."""
    roster_paths = [path for row in slices() for path in row.paths]
    assert roster_paths, "the roster must not be empty"
    assert all("test_testing" not in path for path in roster_paths)


def test_an_unknown_slice_is_the_404_envelope_naming_the_roster(client: TestClient) -> None:
    response = client.post("/api/demo/testing/run/nope")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert "unit-pure" in error["message"]


def test_a_runner_child_process_is_refused_with_the_conflict_envelope(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(RUNNER_CHILD_ENV, "1")
    response = client.post(UNIT_PURE_RUN)
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "conflict"
    assert error["details"]["guardEnv"] == RUNNER_CHILD_ENV


def test_a_real_run_returns_genuine_pytest_output(client: TestClient) -> None:
    body = client.post(UNIT_PURE_RUN).json()
    assert body["outcome"] == "passed"
    assert body["passed"] > 0
    assert body["failed"] == 0
    assert body["durationMs"] > 0
    assert body["pytestSeconds"] is not None and body["pytestSeconds"] > 0
    assert "passed" in body["summaryLine"] and " in " in body["summaryLine"]
    assert body["commandLine"].endswith("tests/domain/test_webhook_signing.py")
    assert body["testLines"], "per-test lines are parsed where cheap"
    assert all(line["outcome"] == "passed" for line in body["testLines"])
    assert body["testLines"][0]["nodeid"].startswith("tests/")


def test_the_testcontainers_slice_shows_its_honest_skips(client: TestClient) -> None:
    """In this container there is no docker.sock — the slice answers its skips.

    Under the host-run fallback (docker.sock mounted) the same slice runs
    for real: both shapes are green, so the assertion accepts either while
    demanding that SOMETHING genuinely ran or skipped.
    """
    body = client.post(TESTCONTAINERS_RUN).json()
    assert body["outcome"] == "passed"
    assert body["passed"] + body["skipped"] > 0
    assert body["durationMs"] > 0
    if body["skipped"] > 0:  # the in-container shape: skips said out loud
        assert "skipped" in body["summaryLine"]


async def test_the_runner_stays_off_the_event_loop(app: FastAPI) -> None:
    """A health probe lands mid-run: the subprocess runs on a worker thread.

    One event loop, two concurrent requests through the REAL app: the run
    (a multi-second subprocess round) and a health probe fired just after
    it. If ``execute_pytest_slice`` blocked the loop, the probe could only
    land after the run finished — healthMs would approximate runMs and the
    ratio below would fail.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        run_started = time.perf_counter()
        run_task = asyncio.create_task(async_client.post(UNIT_PURE_RUN))
        await asyncio.sleep(0.10)  # let the subprocess spawn
        probe_started = time.perf_counter()
        probe = await async_client.get("/api/health")
        probe_ms = (time.perf_counter() - probe_started) * 1000
        run = await run_task
        run_ms = (time.perf_counter() - run_started) * 1000

    assert probe.status_code == 200
    assert run.json()["outcome"] == "passed"
    assert probe_ms < run_ms / 2, (
        f"the health probe took {probe_ms:.0f}ms of a {run_ms:.0f}ms run — "
        "the subprocess is blocking the event loop"
    )


def test_a_pytest_started_by_the_runner_skips_this_module() -> None:
    """The recursion guard, demonstrated: start pytest HERE with the marker."""
    env = {**os.environ, RUNNER_CHILD_ENV: "1"}
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/demo/test_testing_runner_endpoint.py"],
        cwd=str(SERVER_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout[-2000:]
    assert "skipped" in completed.stdout
    assert re.search(r"\d+ passed", completed.stdout) is None, (
        "a runner-started pytest must not run the runner's own endpoint tests"
    )
