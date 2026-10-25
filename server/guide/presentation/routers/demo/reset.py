"""The shared demo reset (``POST /api/demo/reset``) — a terminal-companion utility.

Thin router (family invariant): one POST, no inputs, the use case does
the work, a declared response model. No client panel rides this — it is
the terminal companion's affordance: one call returns every demo state
to its baseline and answers with the honest per-area report (what
really reset, and the stores deliberately never touched). The service
and its participants live in the domain; the wiring lives in the
composition root; this module only resolves the service and calls it.
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request

from guide.core.errors import AppError, FailureKind
from guide.domain.demos.demo_reset import DemoResetService, ResetReport

router = APIRouter(prefix="/api/demo", tags=["demo"])

RESET_PATH: Final = "/reset"
"""The router's one path (prefix-relative) — the terminal companion names it."""


def get_demo_reset_service(request: Request) -> DemoResetService:
    """FastAPI dependency: the reset use case (wired in create_app)."""
    service = request.app.state.demo_reset_service
    if not isinstance(service, DemoResetService):
        raise AppError(FailureKind.INTERNAL, "Demo reset service not wired on app.state")
    return service


DemoResetDep = Annotated[DemoResetService, Depends(get_demo_reset_service)]


@router.post(RESET_PATH, response_model=ResetReport)
async def reset_demo_state(service: DemoResetDep) -> ResetReport:
    """Return every demo state to baseline; report what really happened."""
    return await service.run()
