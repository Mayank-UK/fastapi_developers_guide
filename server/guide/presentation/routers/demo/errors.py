"""The errors explorer demo (topic 30, area ``errors``): panel + probe.

Thin routers (family invariant). The panel is pure payload — the eight kind
rows derived from the taxonomy's own tables. The probe is the ONE endpoint
in the app that honors the scenario store's failure injection (the store's
documented purpose — ``injectFailure`` finally has a live reader): with
``error`` it raises a genuine unhandled ``RuntimeError`` so the OUTERMOST
handler answers the generic 500 envelope (the request id reaching it through
the scope mirror, not the contextvar — the exact path the topic teaches),
with ``latency`` it sleeps out the injection, and with ``none`` it answers
the healthy row. No try/except anywhere: the whole point is what the shared
handlers do with the raise.
"""

import asyncio
from typing import Final

from fastapi import APIRouter

from guide.core.scenario import ScenarioStoreDep
from guide.domain.demos.errors_explorer import (
    ErrorsPanel,
    ProbeRow,
    build_errors_panel,
    build_probe_row,
)

router = APIRouter(prefix="/api/demo/errors", tags=["demo:errors"])

PANEL_PATH: Final = ""
PROBE_ROUTE: Final = "/probe"
"""The routers' paths (prefix-relative) — the terminal companion names them."""

PROBE_LATENCY_SECONDS: Final = 1.5
"""How long the latency injection sleeps — visible to a stopwatch, not painful."""


@router.get(PANEL_PATH, response_model=ErrorsPanel)
async def read_errors_panel() -> ErrorsPanel:
    """The explorer panel: the eight kinds, their triggers, their logs."""
    return build_errors_panel()


@router.get(PROBE_ROUTE, response_model=ProbeRow)
async def probe_scenario_injection(store: ScenarioStoreDep) -> ProbeRow:
    """Answer per the scenario's failure injection — no try/except by design.

    ``injectFailure=error`` raises an unhandled RuntimeError: the last-resort
    handler logs the traceback (with the request id) and answers the generic
    500 envelope, proving internals never leak while the log sees everything.
    ``latency`` sleeps first; ``none`` answers immediately.
    """
    state = store.get()
    if state.inject_failure == "error":
        raise RuntimeError(
            "scenario-injected failure (injectFailure=error) — the outermost "
            "handler turns this into the generic 500 envelope"
        )
    if state.inject_failure == "latency":
        await asyncio.sleep(PROBE_LATENCY_SECONDS)
    return build_probe_row(state)
