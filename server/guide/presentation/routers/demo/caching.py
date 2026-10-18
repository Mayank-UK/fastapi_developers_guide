"""Caching demos: topic 21's lab (area ``caching``).

Thin routers (family invariant). ``GET /posts`` is the topic's REAL
conditional endpoint — it serves the cached posts page through the
``CachedPosts`` port the composition root wires, then applies the pure
conditional helpers: an ETag over the exact bytes served, a
``Cache-Control: no-cache`` policy that forces revalidation, telemetry
headers (``x-cache`` outcome, elapsed ms, age ms, origin counters), and
an ``If-None-Match`` round that ends in a bodyless 304 when the client
already holds the current representation. ``GET /lab`` is the state
panel's roster (one port call, one pure builder); ``POST /invalidate``
and ``POST /stampede`` are the two action buttons — parse, one port
call, return the row. With Redis down every route degrades to the
service_unavailable envelope.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from guide.core.errors import AppError, FailureKind
from guide.domain.caching.conditionals import RESPONSE_CACHE_CONTROL, etag_matches
from guide.domain.caching.ports import (
    CachedPosts,
    CacheFetchRow,
    InvalidationRow,
    StampedeRequest,
    StampedeRow,
)
from guide.domain.demos.caching_lab import CachingLabPayload, build_caching_lab_payload
from guide.domain.posts.entities import PostPage

router = APIRouter(prefix="/api/demo/caching", tags=["demo:caching"])

POSTS_PATH = "/posts"
"""The real conditional endpoint's path under this router — the tour names it."""


def get_caching_service(request: Request) -> CachedPosts:
    """FastAPI dependency: the cache-aside service (wired in create_app)."""
    service = request.app.state.caching_service
    if not isinstance(service, CachedPosts):
        raise AppError(FailureKind.INTERNAL, "Caching service not wired on app.state")
    return service


CachedPostsDep = Annotated[CachedPosts, Depends(get_caching_service)]


def _telemetry_headers(row: CacheFetchRow) -> dict[str, str]:
    """The conditional endpoint's telemetry header set, from one fetch row."""
    headers = {
        "x-cache": row.outcome,
        "x-cache-key": row.key,
        "x-cache-elapsed-ms": str(row.elapsed_ms),
        "x-cache-origin-fetches": str(row.telemetry.misses),
        "x-cache-hits": str(row.telemetry.hits + row.telemetry.coalesced),
    }
    if row.age_ms is not None:
        headers["x-cache-age-ms"] = str(row.age_ms)
    return headers


@router.get(POSTS_PATH, response_model=PostPage)
async def read_cached_posts(service: CachedPostsDep, request: Request) -> Response:
    """Serve the cached posts page — a REAL conditional endpoint.

    The 200 body is the cached canonical JSON verbatim (the declared
    ``PostPage`` response model documents its shape); the ETag covers
    exactly those bytes, and a matching ``If-None-Match`` answers 304
    with the same validators and NO body — the round trip costs nothing
    to transfer and, on a hit, nothing to compute.
    """
    row = await service.fetch_page()
    headers = {
        "etag": row.etag,
        "cache-control": RESPONSE_CACHE_CONTROL,
        **_telemetry_headers(row),
    }
    if etag_matches(request.headers.get("if-none-match"), row.etag):
        return Response(status_code=304, headers=headers)
    return Response(content=row.payload, media_type="application/json", headers=headers)


@router.get("/lab", response_model=CachingLabPayload)
async def read_caching_lab(service: CachedPostsDep) -> CachingLabPayload:
    """Serve the lab roster: namespace, key, TTL, cost label, endpoints, state."""
    state = await service.state()
    return build_caching_lab_payload(
        state=state,
        posts_endpoint=f"{router.prefix}{POSTS_PATH}",
        invalidate_endpoint=f"{router.prefix}/invalidate",
        stampede_endpoint=f"{router.prefix}/stampede",
    )


@router.post("/invalidate", response_model=InvalidationRow)
async def invalidate_cache(service: CachedPostsDep) -> InvalidationRow:
    """The invalidate button: delete the entry, report what happens next."""
    return await service.invalidate()


@router.post("/stampede", response_model=StampedeRow)
async def run_stampede(
    service: CachedPostsDep, request: StampedeRequest
) -> StampedeRow:
    """The stampede button: N concurrent cold reads, single-flight proof."""
    return await service.stampede(request.requests)
