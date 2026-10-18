"""The testing-runner demo (topic 34, area ``testing``): roster + real runs.

Thin router (family invariant): the panel is a pure payload; the run
endpoint validates the requested slice against the frozen roster (the
wire accepts a slice ID, never a path — the allowlist IS the recursion
guard's first wall), refuses to fire when this process itself carries the
runner-child marker (the belt: a runner-started server could re-enter),
and executes the slice OFF the event loop — ``asyncio.to_thread`` wraps
the blocking subprocess, which is itself one of the topic's teaching
points. Every count and duration in the answer comes from the real round.
"""

import asyncio
import os
from typing import Final

from fastapi import APIRouter

from guide.core.errors import AppError, FailureKind
from guide.domain.demos.testing_runner import (
    RUNNER_CHILD_ENV,
    SliceRunResult,
    TestingRunnerPayload,
    TestingSlice,
    build_testing_runner_payload,
    execute_pytest_slice,
    slice_by_id,
    slices,
)

router = APIRouter(prefix="/api/demo/testing", tags=["demo:testing"])

PANEL_PATH: Final = ""
RUN_ROUTE: Final = "/run/{slice_id}"
"""The routers' paths (prefix-relative) — the terminal companion names them."""


@router.get(PANEL_PATH, response_model=TestingRunnerPayload)
async def read_testing_runner() -> TestingRunnerPayload:
    """Serve the roster: curated slices, the client recipe, the mechanics."""
    return build_testing_runner_payload()


@router.post(RUN_ROUTE, response_model=SliceRunResult, response_model_exclude_none=True)
async def run_testing_slice(slice_id: str) -> SliceRunResult:
    """Execute one roster slice for real — in a subprocess, off the loop.

    Unknown slice ids are the shared 404 envelope (the roster is the whole
    vocabulary); a process already marked as a runner child answers the 409
    conflict envelope instead of recursing.
    """
    if os.environ.get(RUNNER_CHILD_ENV):
        raise AppError(
            FailureKind.CONFLICT,
            "This process is already a runner-started child — refusing to nest pytest runs.",
            details={"guardEnv": RUNNER_CHILD_ENV},
        )
    roster: tuple[TestingSlice, ...] = slices()
    slice_: TestingSlice | None = slice_by_id(slice_id)
    if slice_ is None:
        known = ", ".join(candidate.slice_id for candidate in roster)
        raise AppError(
            FailureKind.NOT_FOUND,
            f"Unknown test slice {slice_id!r}; the roster holds: {known}.",
        )
    return await asyncio.to_thread(execute_pytest_slice, slice_)
