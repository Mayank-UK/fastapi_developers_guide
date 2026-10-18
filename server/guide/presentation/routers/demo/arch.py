"""The architecture tracer demo (topic 32, area ``arch``).

Thin router (family invariant): the handler collects the introspection
facts from the RUNNING app — the built middleware chain walked from the
outermost layer down to the app's own router (public surface only:
``middleware_stack`` / ``build_middleware_stack()``, each layer's ``app``
attribute, identity against ``app.router``), the traced endpoint's real
dependency tree (read off the posts resource's own router — the source
router's APIRoute objects, never the post-0.143 wrapped ``app.routes``),
and the composition root's actual wiring (the adapter behind the posts
port, read off ``app.state`` with the same isinstance guard the provider
uses) — and the engine in ``guide/domain/demos/`` drives two REAL internal
requests through the real app at the ASGI boundary and shapes the payload.
"""

import inspect
from typing import Final

from fastapi import APIRouter, FastAPI, Request
from fastapi.routing import APIRoute
from starlette.types import ASGIApp

from guide.core.errors import AppError, FailureKind
from guide.domain.demos.arch_tracer import (
    ArchDependency,
    ArchRoute,
    ArchTracerPayload,
    ArchWiring,
    build_arch_tracer_payload,
)
from guide.domain.posts.ports import PostRepository
from guide.domain.posts.use_cases import PostUseCases
from guide.presentation.routers import posts as posts_resource

router = APIRouter(prefix="/api/demo/arch", tags=["demo:arch"])

TRACER_PATH: Final = "/tracer"
"""The routers' path (prefix-relative) — the terminal companion names it."""

TRACED_TEMPLATE: Final = "/api/posts"
"""The endpoint the tracer follows through every layer (topic 11's resource)."""


def _built_stack_names(app: FastAPI) -> list[str]:
    """Walk the built chain outermost → the app's own router (the terminal)."""
    stack: ASGIApp = app.middleware_stack or app.build_middleware_stack()
    names: list[str] = []
    node: object = stack
    while node is not None and node is not app.router:
        names.append(type(node).__name__)
        node = getattr(node, "app", None)
    if node is not app.router:
        raise AppError(FailureKind.INTERNAL, "The middleware stack walk never reached the router.")
    names.append(type(app.router).__name__)
    return names


def _provider_kind(call: object) -> str:
    """A class provider (a pydantic model) or a callable one (a function)."""
    return "model" if inspect.isclass(call) else "function"


def _provider_name(call: object) -> str:
    """The provider's own name (class or function); a type name as fallback."""
    named = getattr(call, "__name__", None)
    return named if isinstance(named, str) else type(call).__name__


def _traced_route_facts() -> ArchRoute:
    """The traced endpoint's declared shape, from the source router's own routes."""
    for base in posts_resource.router.routes:
        if (
            isinstance(base, APIRoute)
            and base.path == TRACED_TEMPLATE
            and "GET" in (base.methods or set())
        ):
            return ArchRoute(
                template=base.path,
                method="GET",
                endpoint=base.endpoint.__name__,
                response_model=(base.response_model.__name__ if base.response_model else "None"),
                dependencies=[
                    ArchDependency(
                        param=dependency.name,
                        provider=_provider_name(dependency.call),
                        provider_kind=_provider_kind(dependency.call),
                    )
                    for dependency in base.dependant.dependencies
                ],
            )
    raise AppError(
        FailureKind.INTERNAL, f"The traced route {TRACED_TEMPLATE} was not found on its router."
    )


def _wiring_facts(app: FastAPI) -> ArchWiring:
    """What the composition root actually wired — read off the live app.state."""
    bundle = app.state.posts_use_cases
    if not isinstance(bundle, PostUseCases):
        raise AppError(FailureKind.INTERNAL, "Post use cases not wired on app.state")
    adapter = app.state.posts_repository
    if not isinstance(adapter, PostRepository):
        raise AppError(FailureKind.INTERNAL, "Post repository not wired on app.state")
    return ArchWiring(
        port=PostRepository.__name__,
        adapter=type(adapter).__name__,
        use_cases=PostUseCases.__name__,
        wired_by="create_app()",
    )


@router.get(TRACER_PATH, response_model=ArchTracerPayload)
async def read_arch_tracer(request: Request) -> ArchTracerPayload:
    """Serve the live architecture trace: structure, wiring, two real rounds."""
    app = request.app
    return await build_arch_tracer_payload(
        app=app,
        stack_names=_built_stack_names(app),
        user_middleware_names=[m.cls.__name__ for m in app.user_middleware],
        route=_traced_route_facts(),
        wiring=_wiring_facts(app),
    )
