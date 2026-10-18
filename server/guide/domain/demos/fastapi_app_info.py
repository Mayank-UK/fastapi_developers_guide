"""FastAPI app-info demo payload: the running app, introduced by itself.

``GET /api/demo/fastapi/app-info`` serves this payload. The endpoint's
point is introspection through PUBLIC API surface only: the app's
identity (title, version — the same facts /docs displays), the
environment config it booted in, the URLs of the framework's built-in
documentation mounts, the versions of the three libraries that ARE the
stack, the middleware and exception handlers the factory registered,
and the route table.

The route table is built from ``app.openapi()["paths"]`` — deliberately
NOT from ``app.routes``: since 0.143 FastAPI's ``include_router`` wraps
included routers, and the wrapping entries do not expose ``.path``. The
OpenAPI schema is the stable public view of exactly the DECLARED API
surface (implicit HEAD/OPTIONS never appear in it because FastAPI does
not route them implicitly — topic 03's 405 probe), and
``app.openapi()`` caches its result on first call, so the demo does not
pay schema generation per request.

The builder is pure: plain data in (the router collects every fact from
the live app), payload out — the same contract as the other demo
builders.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from guide.core.serialization import CamelModel

_HTTP_METHODS: Final[frozenset[str]] = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)
"""The operation keys an OpenAPI path item can carry; anything else is metadata."""


class DocsMounts(CamelModel):
    """Where the framework's built-in documentation surfaces live."""

    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None


class StackVersions(CamelModel):
    """The three libraries that ARE this app's web stack."""

    fastapi: str
    starlette: str
    pydantic: str


class HandlerRegistration(CamelModel):
    """One exception handler registered on the app (exception → handler)."""

    exception: str
    handler: str


class RouteEntry(CamelModel):
    """One path in the app's declared API: its methods and tags."""

    path: str
    methods: list[str]
    tags: list[str]


class FastApiAppInfoPayload(CamelModel):
    """Wire shape of ``GET /api/demo/fastapi/app-info`` (camelCase)."""

    title: str
    version: str
    environment: str
    docs: DocsMounts
    stack: StackVersions
    middleware: list[str]
    exception_handlers: list[HandlerRegistration]
    routes: list[RouteEntry]


def _route_entry(path: str, item: Mapping[str, Any]) -> RouteEntry:
    """Extract one route row: declared methods uppercased, tags unioned."""
    methods = sorted(key.upper() for key in item if key in _HTTP_METHODS)
    tags = sorted(
        {
            tag
            for key, operation in item.items()
            if key in _HTTP_METHODS
            for tag in _tag_list(operation)
        }
    )
    return RouteEntry(path=path, methods=methods, tags=tags)


def _tag_list(operation: Mapping[str, Any]) -> tuple[str, ...]:
    """An operation's tags as a tuple; absent or malformed means none."""
    raw = operation.get("tags")
    if not isinstance(raw, list):
        return ()
    return tuple(tag for tag in raw if isinstance(tag, str))


def build_app_info_payload(
    *,
    title: str,
    version: str,
    environment: str,
    docs_url: str | None,
    redoc_url: str | None,
    openapi_url: str | None,
    stack: Mapping[str, str],
    middleware_names: Sequence[str],
    handler_names: Mapping[str, str],
    paths: Mapping[str, Mapping[str, Any]],
) -> FastApiAppInfoPayload:
    """Shape the live app's collected facts into the payload (pure, no I/O)."""
    return FastApiAppInfoPayload(
        title=title,
        version=version,
        environment=environment,
        docs=DocsMounts(docs_url=docs_url, redoc_url=redoc_url, openapi_url=openapi_url),
        stack=StackVersions(
            fastapi=stack["fastapi"], starlette=stack["starlette"], pydantic=stack["pydantic"]
        ),
        middleware=list(middleware_names),
        exception_handlers=[
            HandlerRegistration(exception=exception, handler=handler)
            for exception, handler in sorted(handler_names.items())
        ],
        routes=[_route_entry(path, paths[path]) for path in sorted(paths)],
    )
