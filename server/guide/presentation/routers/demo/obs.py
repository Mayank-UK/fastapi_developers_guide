"""The observability demos (topic 33, area ``obs``): viewer + trace.

Thin routers (family invariant): one GET each, pure payload builders,
declared response models. The viewer introspects the live structlog
pipeline and serves the process's real recent log events (its own two
beats included, stamped with this request's id); the trace drives three
REAL internal requests through the app at the ASGI boundary — one per
outcome class — and correlates each round's derived request id across the
echoed header, the error envelope, and the log rows it produced.
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request

from guide.core.config import AppConfig, get_config
from guide.core.request_context import resolve_request_id
from guide.domain.demos.obs_trace import TraceFanout, build_trace_fanout_payload
from guide.domain.demos.obs_viewer import LogViewerPanel, build_log_viewer_payload

router = APIRouter(prefix="/api/demo/obs", tags=["demo:obs"])

VIEWER_PATH: Final = "/viewer"
TRACE_PATH: Final = "/trace"
"""The two paths (prefix-relative) — the terminal companion names them."""


@router.get(VIEWER_PATH, response_model=LogViewerPanel)
async def read_log_viewer(
    request: Request, config: Annotated[AppConfig, Depends(get_config)]
) -> LogViewerPanel:
    """Serve the live structured-log viewer: pipeline, level, recent events."""
    return build_log_viewer_payload(
        request_id=resolve_request_id(request),
        configured_level=config.log_level,
    )


@router.get(TRACE_PATH, response_model=TraceFanout)
async def read_trace_fanout(request: Request) -> TraceFanout:
    """Serve the live trace fan-out: three real rounds, one correlated id each."""
    return await build_trace_fanout_payload(
        app=request.app,
        root_request_id=resolve_request_id(request),
    )
