"""Routing demo API: ``GET /api/demo/routing/explorer`` — the route matcher.

Thin router (family invariant): the handler validates the simulated request
line — ``method`` is a Literal so an unknown verb is rejected as the 422
envelope, ``path`` must look like an absolute path (optionally with a query
string) — collects the declared route table from the app's public OpenAPI
schema, and the pure builder in ``guide/domain/demos/`` does the matching.
The endpoint is its own best example: its two query parameters, one with a
default and one pattern-validated, are exactly the machinery the topic's
path-and-query section teaches.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Request
from pydantic import Field

from guide.domain.demos.routing_explorer import (
    RoutingExplorerPayload,
    build_routing_explorer_payload,
)

router = APIRouter(prefix="/api/demo/routing", tags=["demo:routing"])

ExplorerMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
"""The verbs a caller may simulate (TRACE never reaches a JSON API in practice)."""

_PATH_PATTERN: str = r"^/[^?#]*(?:\?[^#]*)?$"
"""Absolute path, optional query string — exactly what a browser location carries."""


@router.get(
    "/explorer", response_model=RoutingExplorerPayload, response_model_exclude_none=True
)
def read_routing_explorer(
    request: Request,
    method: ExplorerMethod = "GET",
    path: Annotated[str, Field(pattern=_PATH_PATTERN)] = "/api/health",
) -> RoutingExplorerPayload:
    """Match one simulated method+path against the app's declared route table."""
    return build_routing_explorer_payload(
        method=method,
        path=path,
        paths=request.app.openapi()["paths"],
    )
