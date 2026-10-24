"""The circuit-breaker demo (topic 39, area ``reliability``).

Thin router (family invariant): one GET, the payload builder does the
work, a declared response model. The panel walks a REAL CircuitBreaker
(the pure substrate in ``guide.domain.reliability.breaker``) through one
full cycle on every request — successes, accumulating failures, the trip,
two fast-failed calls (dependency never touched), the logical elapse of
the open timeout, the half-open probe, recovery — with per-call state and
latency evidence measured on the request that serves it.
"""

from typing import Final

from fastapi import APIRouter

from guide.domain.demos.reliability_breaker import BreakerPanel, build_breaker_panel

router = APIRouter(prefix="/api/demo/reliability", tags=["demo:reliability"])

BREAKER_PATH: Final = "/breaker"
"""The router's one path (prefix-relative) — the terminal companion names it."""


@router.get(BREAKER_PATH, response_model=BreakerPanel)
async def read_breaker_panel() -> BreakerPanel:
    """Serve the live breaker cycle: closed → open → half-open → closed."""
    return await build_breaker_panel()
