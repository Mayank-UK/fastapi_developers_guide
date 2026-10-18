"""The rate-limit dependency: burn a budget, answer 429 with Retry-After.

The seam between the pure limiter and the HTTP world. A route declares
``Depends(enforce_rate_limit)`` and that IS its throttle: the dependency
resolves the per-app ``SlidingWindowLimiter`` from ``app.state``, keys the
budget by CLIENT IP + ROUTE TEMPLATE (the template, not the raw path, so
``/posts/a`` and ``/posts/b`` share one budget instead of getting one
each), and hands the handler the verdict on success — remaining budget
rides the wire as ``x-ratelimit-remaining`` so honest clients can slow
down before they are told to.

A denial raises the standard envelope as ``rate_limited`` (429) with the
``Retry-After`` header attached through ``AppError.headers`` — the taxonomy
owns the status, the header is part of the status's contract, and the
envelope's ``details`` carry the numbers (limit, window, retryAfterSeconds)
for programs that prefer structured fields to response headers. The
``Retry-After`` value is the engine's floating-point instant rounded UP to
whole seconds (a client told "try in 2.1s" must not try in 2) and never
zero (a denial always owes at least one second of patience).
"""

import math
from typing import Annotated, Final

from fastapi import Depends, Request
from starlette.routing import Route

from guide.core.errors import AppError, FailureKind
from guide.domain.security.rate_limit import RateLimitVerdict, SlidingWindowLimiter

UNKNOWN_CLIENT: Final = "unknown"
"""The key prefix when the ASGI scope carries no client (a bare in-process
call) — it still buckets, just per route rather than per caller."""

RATE_LIMIT_REMAINING_HEADER: Final = "x-ratelimit-remaining"
"""Success-path telemetry: how many hits this key has left in its window."""


def get_rate_limiter(request: Request) -> SlidingWindowLimiter:
    """FastAPI dependency: the per-app limiter (wired in create_app)."""
    limiter = request.app.state.rate_limiter
    if not isinstance(limiter, SlidingWindowLimiter):
        raise AppError(FailureKind.INTERNAL, "Rate limiter not wired on app.state")
    return limiter


def client_key(request: Request) -> str:
    """The budget key: client IP + route template (raw path as fallback).

    ``request.client`` is the socket's view — honest for direct dev
    traffic and, behind a proxy, whatever the proxy forwarded (a real
    deployment keys on the proxy's forwarded-for header instead; the topic
    teaches that exact caveat). The route TEMPLATE keeps parameterized
    paths on one shared budget.
    """
    client_ip = request.client.host if request.client is not None else UNKNOWN_CLIENT
    route = request.scope.get("route")
    template = route.path if isinstance(route, Route) else request.url.path
    return f"{client_ip}:{template}"


async def enforce_rate_limit(request: Request) -> RateLimitVerdict:
    """Consume one unit for this caller+route, or raise the 429 envelope."""
    limiter = get_rate_limiter(request)
    verdict = limiter.hit(client_key(request))
    if verdict.allowed:
        return verdict
    retry_after_s = max(1, math.ceil(verdict.retry_after_s or 0))
    raise AppError(
        FailureKind.RATE_LIMITED,
        (
            f"rate limit exceeded — {verdict.limit} requests per "
            f"{verdict.window_s:g}s per {limiter.policy.keying}; retry in "
            f"{retry_after_s}s"
        ),
        details={
            "limit": verdict.limit,
            "windowSeconds": verdict.window_s,
            "retryAfterSeconds": retry_after_s,
            "keying": limiter.policy.keying,
        },
        headers={"Retry-After": str(retry_after_s)},
    )


RateLimitDep = Annotated[RateLimitVerdict, Depends(enforce_rate_limit)]
"""Declare on a route to give it a real throttle — the verdict rides in."""
