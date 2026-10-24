"""The stall-diagnosis demo (topic 35, area ``debug``): measure, don't guess.

Thin router (family invariant): one GET, the payload builder does the
work, a declared response model. The panel runs four bounded phases — an
async await, a threadpool-contained block, an on-loop block, and a
baseline — with real instruments around each: elapsed, event-loop lag
from a concurrent probe, a REAL internal ``GET /api/health`` driven
through the app mid-phase, a real tracemalloc window, and the request's
own correlated log rows from the recent-events ring.
"""

from typing import Final

from fastapi import APIRouter, Request

from guide.core.request_context import resolve_request_id
from guide.domain.demos.debug_stall import StallPanel, build_stall_payload

router = APIRouter(prefix="/api/demo/debug", tags=["demo:debug"])

STALL_PATH: Final = "/stall"
"""The router's one path (prefix-relative) — the terminal companion names it."""


@router.get(STALL_PATH, response_model=StallPanel)
async def read_stall_panel(request: Request) -> StallPanel:
    """Serve the live stall panel: four bounded phases, measured evidence."""
    return await build_stall_payload(
        app=request.app,
        request_id=resolve_request_id(request),
    )
