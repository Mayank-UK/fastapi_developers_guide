"""FastAPI demo API: ``GET /api/demo/fastapi/app-info`` — the app, by itself.

Thin router (family invariant): the handler collects the app's own facts
through public API surface — identity and docs URLs from the FastAPI
instance, the registered middleware and exception handlers, the OpenAPI
route table (``app.openapi()`` caches after the first call), the stack's
own version strings, the environment from the injected config — and the
pure builder in ``guide/domain/demos/`` shapes them. Nothing reaches
into private attributes; the payload is honest even where the honest
answer is short (one middleware).
"""

from collections.abc import Mapping
from typing import Annotated, Any

import fastapi
import pydantic
import starlette
from fastapi import APIRouter, Depends, Request

from guide.core.config import AppConfig, get_config
from guide.domain.demos.fastapi_app_info import FastApiAppInfoPayload, build_app_info_payload

router = APIRouter(prefix="/api/demo/fastapi", tags=["demo:fastapi"])


def _stack_versions() -> dict[str, str]:
    """The web stack's own version strings (module attributes, public)."""
    return {
        "fastapi": fastapi.__version__,
        "starlette": starlette.__version__,
        "pydantic": pydantic.VERSION,
    }


def _handler_names(
    handlers: Mapping[type[BaseException] | int, Any],
) -> dict[str, str]:
    """Display names for the registered handlers, keyed by exception name."""

    def name_of(key: type[BaseException] | int) -> str:
        return key.__name__ if isinstance(key, type) else str(key)

    return {
        name_of(key): getattr(value, "__qualname__", repr(value))
        for key, value in handlers.items()
    }


@router.get("/app-info", response_model=FastApiAppInfoPayload)
def read_app_info(
    request: Request, config: Annotated[AppConfig, Depends(get_config)]
) -> FastApiAppInfoPayload:
    """Introspect the running app: identity, stack, wiring, and route table."""
    app = request.app
    return build_app_info_payload(
        title=app.title,
        version=app.version,
        environment=config.env,
        docs_url=app.docs_url,
        redoc_url=app.redoc_url,
        openapi_url=app.openapi_url,
        stack=_stack_versions(),
        middleware_names=[middleware.cls.__name__ for middleware in app.user_middleware],
        handler_names=_handler_names(app.exception_handlers),
        paths=app.openapi()["paths"],
    )
