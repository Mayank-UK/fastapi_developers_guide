"""Middleware demo API: ``GET /api/demo/middleware/pipeline`` — the live onion.

Thin router (family invariant): the handler collects the REAL composition
facts from the running app — the built middleware chain walked from the
outermost layer down to the app's own router (public surface only:
``middleware_stack`` / ``build_middleware_stack()``, each layer's ``app``
attribute, identity against ``app.router``), the registered user
middleware names, and the ambient request id the REAL RequestIdMiddleware
assigned before this handler started — and the pure engine in
``guide/domain/demos/`` runs the traced pipeline and shapes the payload.
The response itself is half the demo: its ``x-request-id`` header is
stamped by the real middleware AFTER the payload is built.
"""

from fastapi import APIRouter, FastAPI, Request
from starlette.types import ASGIApp

from guide.core.errors import AppError, FailureKind
from guide.core.request_context import current_request_id
from guide.domain.demos.middleware_pipeline import (
    MiddlewarePipelinePayload,
    build_middleware_pipeline_payload,
)

router = APIRouter(prefix="/api/demo/middleware", tags=["demo:middleware"])


def _built_stack_names(app: FastAPI) -> list[str]:
    """Walk the built chain outermost → the app's own router (the terminal)."""
    stack: ASGIApp = app.middleware_stack or app.build_middleware_stack()
    names: list[str] = []
    node: object = stack
    while node is not None and node is not app.router:
        names.append(type(node).__name__)
        node = getattr(node, "app", None)
    if node is not app.router:
        raise AppError(
            FailureKind.INTERNAL, "The middleware stack walk never reached the router."
        )
    names.append(type(app.router).__name__)
    return names


@router.get("/pipeline", response_model=MiddlewarePipelinePayload)
async def read_middleware_pipeline(request: Request) -> MiddlewarePipelinePayload:
    """Serve the live middleware chain: composition, traced wrap order, request id."""
    user_names = [middleware.cls.__name__ for middleware in request.app.user_middleware]
    return await build_middleware_pipeline_payload(
        stack_names=_built_stack_names(request.app),
        user_middleware_names=user_names,
        request_id=current_request_id(),
    )
