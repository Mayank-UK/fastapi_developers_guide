"""The testing-runner builder: roster purity + the pytest-output parser.

The roster is the recursion guard's first wall, so its purity is pinned
here: only the four frozen slice ids exist, every path is a real file
under tests/, and nothing in the roster can reach the demo's own tests.
The parser is pinned against every pytest output shape it can meet —
green rounds, failures, nothing collected, internal errors, and output
that is empty to the last byte.
"""

import os
import re
from pathlib import Path

import pytest

from guide.domain.demos.testing_runner import (
    RUN_TIMEOUT_SECONDS,
    _timeout_result,
    build_testing_runner_payload,
    execute_pytest_slice,
    parse_pytest_output,
    slice_by_id,
    slices,
)

EXPECTED_SLICE_IDS: tuple[str, ...] = (
    "unit-pure",
    "fixtures-testclient",
    "async-native",
    "testcontainers-skips",
)

SERVER_ROOT: Path = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    bool(os.environ.get("FDG_TEST_RUNNER_CHILD")),
    reason="runner-started pytest never re-reaches the runner's own engine",
)


def test_the_roster_is_the_four_frozen_slices_in_order() -> None:
    assert tuple(candidate.slice_id for candidate in slices()) == EXPECTED_SLICE_IDS
    assert slice_by_id("unit-pure") is not None
    assert slice_by_id("nope") is None


def test_every_roster_path_is_a_real_file_under_tests() -> None:
    for candidate in slices():
        assert candidate.paths, f"slice {candidate.slice_id} needs at least one path"
        for path in candidate.paths:
            assert path.startswith("server/tests/"), path
            assert (SERVER_ROOT / path.removeprefix("server/")).is_file(), path


def test_the_roster_can_never_reach_the_runner_s_own_tests() -> None:
    """Recursion guard, wall one: the allowlist holds no runner-adjacent path."""
    for candidate in slices():
        for path in candidate.paths:
            assert "test_testing" not in path, path
            assert "conftest" not in path, path


def test_the_panel_names_the_guard_the_timeout_and_the_recipe() -> None:
    payload = build_testing_runner_payload()
    assert payload.facts.guard_env == "FDG_TEST_RUNNER_CHILD"
    assert payload.facts.timeout_seconds == RUN_TIMEOUT_SECONDS
    assert "asyncio.to_thread" in payload.facts.off_loop
    assert "npm test" in payload.client_recipe.command
    assert payload.client_recipe.note  # the recipe explains itself, never fakes a run
    assert payload.reasoning


def test_parse_green_round_counts_and_per_test_lines() -> None:
    stdout = "\n".join(
        [
            "tests/domain/test_webhook_signing.py::test_round_trip PASSED [ 12%]",
            "tests/domain/test_webhook_signing.py::test_scheme_is_hex PASSED [ 25%]",
            "",
            "====================== 2 passed in 0.31s =======================",
        ]
    )
    result = parse_pytest_output(
        slice_id="unit-pure",
        stdout=stdout,
        exit_code=0,
        duration_ms=412.5,
        command_line="python -m pytest -v tests/",
        note="note",
    )
    assert result.outcome == "passed"
    assert result.passed == 2
    assert result.failed == 0
    assert result.skipped == 0
    assert result.pytest_seconds == 0.31
    assert result.duration_ms == 412.5
    assert [line.outcome for line in result.test_lines] == ["passed", "passed"]
    assert result.test_lines[0].nodeid.endswith("test_round_trip")
    assert "2 passed in 0.31s" in result.summary_line


def test_parse_failure_round_reports_the_verdict_and_the_lines() -> None:
    stdout = "\n".join(
        [
            "tests/x.py::test_ok PASSED [ 50%]",
            "tests/x.py::test_bad FAILED [100%]",
            "=================== 1 failed, 1 passed in 0.84s ===================",
        ]
    )
    result = parse_pytest_output(
        slice_id="x", stdout=stdout, exit_code=1, duration_ms=900.0, command_line="pytest", note=""
    )
    assert result.outcome == "failed"
    assert result.passed == 1
    assert result.failed == 1
    assert {line.outcome for line in result.test_lines} == {"passed", "failed"}


def test_parse_skip_round_and_error_counts() -> None:
    stdout = "================== 5 skipped in 0.62s =================="
    result = parse_pytest_output(
        slice_id="x", stdout=stdout, exit_code=0, duration_ms=700.0, command_line="pytest", note=""
    )
    assert result.outcome == "passed"  # pytest's own verdict on skips
    assert result.skipped == 5
    assert result.passed == 0


def test_parse_nothing_collected_is_its_own_verdict() -> None:
    result = parse_pytest_output(
        slice_id="x",
        stdout="no tests ran in 0.01s",
        exit_code=5,
        duration_ms=20.0,
        command_line="pytest",
        note="",
    )
    assert result.outcome == "no_tests_ran"
    assert result.passed == 0 and result.skipped == 0
    assert result.test_lines == []


def test_parse_internal_error_keeps_the_raw_last_line_honest() -> None:
    result = parse_pytest_output(
        slice_id="x",
        stdout="ImportError: something broke\n",
        exit_code=3,
        duration_ms=500.0,
        command_line="pytest",
        note="",
    )
    assert result.outcome == "internal_error"
    assert result.summary_line == "ImportError: something broke"
    assert result.pytest_seconds is None


def test_parse_empty_output_still_answers_a_shape() -> None:
    result = parse_pytest_output(
        slice_id="x", stdout="", exit_code=3, duration_ms=10.0, command_line="pytest", note=""
    )
    assert result.outcome == "internal_error"
    assert result.summary_line == "(no output)"


def test_the_timeout_result_invents_nothing() -> None:
    result = _timeout_result(slice_id="x", duration_ms=90_000.0, command_line="pytest", note="n")
    assert result.outcome == "timeout"
    assert result.passed == 0 and result.failed == 0 and result.skipped == 0
    assert re.search(r"timed out after \d+s", result.summary_line)
    assert result.test_lines == []


def test_execute_reports_the_command_and_cwd_it_really_used() -> None:
    """One real round against the fastest slice: the argv is ours, verbatim."""
    slice_ = slice_by_id("unit-pure")
    assert slice_ is not None
    result = execute_pytest_slice(slice_)
    assert "-m" in result.command_line and "pytest" in result.command_line
    assert result.outcome == "passed"
    assert result.passed > 0
    assert result.duration_ms > 0
