"""Testing-runner demo: the repo's own suite, executed for real (topic 34).

``GET /api/demo/testing`` serves the roster — four CURATED slices of this
repository's real test files, each one a teaching exemplar for one layer of
the pyramid (a pure unit file, the conftest-fixture + TestClient file, an
async-native file, and the testcontainers file whose in-container skips are
themselves the lesson). ``POST /api/demo/testing/run/{slice_id}`` executes
one slice honestly: ``<venv python> -m pytest -v --no-header <paths>`` in a
subprocess (cwd = the server root), off the event loop via
``asyncio.to_thread`` — a subprocess is exactly the kind of blocking call
that must never sit on the loop — with a hard timeout and the raw output
parsed into typed counts, per-test lines, and the pytest exit verdict.

Two honesty rules shape the payload. First, the runner RUNS what it shows:
every count, duration, and per-test line in a run result comes from the
real subprocess round, never composed. Second, the client's vitest suite
CANNOT run from the server (it lives in the client container's node
toolchain) — it appears as a recipe row that names the real command, and
the panel never fakes a run it did not make.

Recursion guard (the known trap of a test-runner that is itself tested):
the roster is an explicit allowlist — the wire accepts a slice ID, never a
path, so no request can steer argv at the demo's own tests — and every
runner-started pytest carries ``FDG_TEST_RUNNER_CHILD=1`` in its
environment; the demo's own endpoint-test module skips itself when it
sees that marker, so a runner-started suite can never reach (and re-fire)
the runner. The run endpoint also refuses to fire when ITS process carries
the marker — the belt behind the suspenders.
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Final, Literal

from guide.core.serialization import CamelModel

RUNNER_CHILD_ENV: Final = "FDG_TEST_RUNNER_CHILD"
"""Env marker every runner-started pytest carries — the recursion guard."""

RUN_TIMEOUT_SECONDS: Final = 90.0
"""Hard subprocess timeout; the curated slices finish in single-digit seconds."""

_SERVER_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
"""guide/domain/demos → guide/domain → guide → server/ (owns pyproject + tests/)."""

_PYTEST_FLAGS: Final[tuple[str, ...]] = ("-v", "--no-header")
"""Verbose enough for per-test lines, headerless enough to stay compact."""

SliceOutcome = Literal["passed", "failed", "no_tests_ran", "timeout", "internal_error"]
"""The run's verdict: pytest's exit code mapped honestly (5 = nothing ran)."""

LineOutcome = Literal["passed", "failed", "error", "skipped", "xfail", "xpass"]
"""One test's verdict as pytest -v prints it."""


class TestingSlice(CamelModel):
    """One curated slice of the repo's real suite, runnable by the demo."""

    slice_id: str
    title: str
    focus: str
    paths: list[str]
    """Repo-root-relative display paths (the wire shows what the reader can open)."""
    note: str
    """What to watch for when this slice runs."""


class ClientRecipe(CamelModel):
    """How the client's vitest suite is really invoked — a recipe, not a run."""

    title: str
    command: str
    note: str


class RunnerFacts(CamelModel):
    """How the runner executes slices — the mechanics, stated plainly."""

    command_template: str
    cwd: str
    timeout_seconds: float
    off_loop: str
    guard_env: str


class TestingRunnerPayload(CamelModel):
    """Wire shape of ``GET /api/demo/testing``."""

    slices: list[TestingSlice]
    client_recipe: ClientRecipe
    facts: RunnerFacts
    reasoning: str


class SliceTestLine(CamelModel):
    """One per-test line parsed from pytest -v output."""

    nodeid: str
    outcome: LineOutcome


class SliceRunResult(CamelModel):
    """Wire shape of ``POST /api/demo/testing/run/{slice_id}`` — measured, not composed."""

    slice_id: str
    outcome: SliceOutcome
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_ms: float
    pytest_seconds: float | None
    """Pytest's own reported duration; None when the summary line did not parse."""
    summary_line: str
    command_line: str
    test_lines: list[SliceTestLine]
    note: str


_SLICES: Final[tuple[TestingSlice, ...]] = (
    TestingSlice(
        slice_id="unit-pure",
        title="Pure unit tests",
        focus="Topic 14's HMAC signer/verifier: pure domain functions, no app, no I/O.",
        paths=["server/tests/domain/test_webhook_signing.py"],
        note=(
            "The pyramid's base — fast, deterministic, and the only kind that"
            " should number in the hundreds."
        ),
    ),
    TestingSlice(
        slice_id="fixtures-testclient",
        title="Fixtures + TestClient",
        focus="The conftest app/client fixtures driving the content wire contract.",
        paths=["server/tests/test_content_routes.py"],
        note=(
            "A fresh app per test via create_app(), sync TestClient over it —"
            " integration at the HTTP edge, in-process."
        ),
    ),
    TestingSlice(
        slice_id="async-native",
        title="Async-native tests",
        focus=(
            "Asyncio tests on the auto event loop (asyncio_mode=auto),"
            " measured timings pinned by invariants."
        ),
        paths=["server/tests/domain/test_runtime_async_builder.py"],
        note="async def tests need no decorator in this repo — the suite's own event-loop answer.",
    ),
    TestingSlice(
        slice_id="testcontainers-skips",
        title="Testcontainers (honest skips)",
        focus="The clean-database round-trip: real throwaway PostgreSQL when Docker is reachable.",
        paths=["server/tests/data/test_orm_testcontainers.py"],
        note=(
            "Inside the dev/verify containers there is no docker.sock — watch every"
            " test SKIP with the reason. The host-run fallback runs them for real."
        ),
    ),
)

_CLIENT_RECIPE: Final = ClientRecipe(
    title="The client's vitest suite (a recipe, not a run)",
    command=(
        "docker exec fastapi_developers_guide_client_dev "
        "bash -lc 'cd /app && npm test'"
    ),
    note=(
        "The 400+ client tests run under vitest inside the client container's "
        "node toolchain — the server cannot execute them, so this panel shows "
        "the real command instead of faking a result."
    ),
)

_RUNNER_FACTS: Final = RunnerFacts(
    command_template="<venv python> -m pytest -v --no-header <slice paths>",
    cwd="server/",
    timeout_seconds=RUN_TIMEOUT_SECONDS,
    off_loop="asyncio.to_thread (a blocking subprocess never sits on the event loop)",
    guard_env=RUNNER_CHILD_ENV,
)

_REASONING: Final = (
    "The panel below is the runner, not a mock: pressing run fires a real "
    "subprocess pytest over this repository's own test files — the same "
    "venv python that serves this page — with a hard timeout, off the event "
    "loop, and every count, duration, and per-test line in the answer is "
    "parsed from that real round. The four slices are frozen: the wire "
    "accepts a slice id, never a path, and each runner-started pytest "
    "carries the guard env marker so it can never reach the runner's own "
    "tests. The testcontainers slice is the honesty exhibit — in this "
    "container it shows its skips with reasons instead of pretending; the "
    "client's vitest suite rides as a recipe row for the same reason: the "
    "panel never fakes a run it did not make."
)

_VERB_LINE: Final = re.compile(r"^(tests/\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b")
"""A pytest -v per-test line: ``tests/…::test_x PASSED [ 12%]``."""

_LINE_OUTCOME_BY_VERB: Final[dict[str, LineOutcome]] = {
    "PASSED": "passed",
    "FAILED": "failed",
    "ERROR": "error",
    "SKIPPED": "skipped",
    "XFAIL": "xfail",
    "XPASS": "xpass",
}

_SUMMARY_TOKENS: Final[tuple[str, ...]] = ("passed", "failed", "skipped", "error", "no tests ran")
"""A final line needs one of these (plus ' in ') to be the pytest summary."""


def slices() -> tuple[TestingSlice, ...]:
    """The frozen roster — the allowlist the run endpoint validates against."""
    return _SLICES


def slice_by_id(slice_id: str) -> TestingSlice | None:
    """One roster slice, or None when the id is unknown."""
    for candidate in _SLICES:
        if candidate.slice_id == slice_id:
            return candidate
    return None


def build_testing_runner_payload() -> TestingRunnerPayload:
    """Compose the roster panel: slices, the client recipe, the mechanics."""
    return TestingRunnerPayload(
        slices=list(_SLICES),
        client_recipe=_CLIENT_RECIPE,
        facts=_RUNNER_FACTS,
        reasoning=_REASONING,
    )


def _server_relative(repo_relative: str) -> str:
    """server/tests/… → tests/… (the subprocess cwd IS the server root)."""
    return repo_relative.removeprefix("server/")


def _find_summary_line(lines: list[str]) -> str:
    """The last line that looks like pytest's ``==== N passed in Xs ====''."""
    for line in reversed(lines):
        stripped = line.strip()
        if " in " in stripped and any(token in stripped for token in _SUMMARY_TOKENS):
            return stripped
    return ""


def _count(summary_line: str, noun: str) -> int:
    """``N <noun>`` out of the summary line; 0 when the noun is absent."""
    match = re.search(rf"(\d+)\s+{noun}\b", summary_line)
    return int(match.group(1)) if match else 0


def parse_pytest_output(
    *,
    slice_id: str,
    stdout: str,
    exit_code: int,
    duration_ms: float,
    command_line: str,
    note: str,
) -> SliceRunResult:
    """Turn one real pytest round into typed results — every shape accounted for.

    Exit-code verdicts follow pytest itself: 0 passed, 1 failures, 5 no tests
    collected, anything else (interrupted, internal error, usage) is an
    internal_error with the raw last line kept honest on the wire.
    """
    lines = [line for line in stdout.splitlines() if line.strip()]
    summary_line = _find_summary_line(lines)
    test_lines = [
        SliceTestLine(nodeid=match.group(1), outcome=_LINE_OUTCOME_BY_VERB[match.group(2)])
        for line in lines
        if (match := _VERB_LINE.match(line.strip())) is not None
    ]
    seconds_match = re.search(r"in\s+([0-9.]+)s", summary_line)
    pytest_seconds = float(seconds_match.group(1)) if seconds_match else None

    if exit_code == 0:
        outcome: SliceOutcome = "passed"
    elif exit_code == 1:
        outcome = "failed"
    elif exit_code == 5:
        outcome = "no_tests_ran"
    else:
        outcome = "internal_error"

    return SliceRunResult(
        slice_id=slice_id,
        outcome=outcome,
        passed=_count(summary_line, "passed"),
        failed=_count(summary_line, "failed"),
        skipped=_count(summary_line, "skipped"),
        errors=_count(summary_line, "error"),
        duration_ms=round(duration_ms, 1),
        pytest_seconds=pytest_seconds,
        summary_line=summary_line or (lines[-1] if lines else "(no output)"),
        command_line=command_line,
        test_lines=test_lines,
        note=note,
    )


def _timeout_result(
    *, slice_id: str, duration_ms: float, command_line: str, note: str
) -> SliceRunResult:
    """The honest timeout answer: no counts invented, the ceiling named."""
    return SliceRunResult(
        slice_id=slice_id,
        outcome="timeout",
        passed=0,
        failed=0,
        skipped=0,
        errors=0,
        duration_ms=round(duration_ms, 1),
        pytest_seconds=None,
        summary_line=f"subprocess timed out after {RUN_TIMEOUT_SECONDS:.0f}s",
        command_line=command_line,
        test_lines=[],
        note=note,
    )


def execute_pytest_slice(slice_: TestingSlice, *, cwd: Path = _SERVER_ROOT) -> SliceRunResult:
    """Run one slice FOR REAL: subprocess pytest, hard timeout, guard env.

    The child inherits this process's environment plus the runner marker —
    so anything the child collects that itself checks the marker (the demo's
    own endpoint tests) steps out of the way instead of recursing.
    """
    argv = [
        sys.executable,
        "-m",
        "pytest",
        *_PYTEST_FLAGS,
        *(_server_relative(path) for path in slice_.paths),
    ]
    command_line = " ".join(argv)
    env = {**os.environ, RUNNER_CHILD_ENV: "1"}
    started = time.perf_counter()
    try:
        # argv is ours end to end: the flags are frozen, the paths come from
        # the roster (never the request) — no shell, no interpolation.
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _timeout_result(
            slice_id=slice_.slice_id,
            duration_ms=(time.perf_counter() - started) * 1000,
            command_line=command_line,
            note=slice_.note,
        )
    return parse_pytest_output(
        slice_id=slice_.slice_id,
        stdout=completed.stdout,
        exit_code=completed.returncode,
        duration_ms=(time.perf_counter() - started) * 1000,
        command_line=command_line,
        note=slice_.note,
    )
