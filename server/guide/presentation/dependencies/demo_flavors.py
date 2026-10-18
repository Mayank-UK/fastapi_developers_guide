"""The dependency-matrix providers: every ``Depends`` shape, as real wiring.

``GET /api/demo/dep/matrix`` resolves ALL of these in one request and
reports identity proofs (rows built by
``guide.domain.demos.dep_matrix.build_matrix_payload``). The flavor objects
are framework-free and live in the domain module; this file is the wiring
layer's half — the callables and instances handlers declare with
``Depends``:

- plain functions (``get_correlation``, ``get_rate_budget``) — cached per
  request by default;
- a paired provider for ``use_cache=False`` (``open_cursor``);
- a three-deep sub-dependency chain (``get_verified_request`` →
  ``get_authenticated_actor`` → ``get_parsed_token``);
- a callable class: an ``ApiKeyIssuer`` INSTANCE — FastAPI calls it per
  request;
- a sync provider (``peek_threadpool``) that makes the threadpool fact
  measurable from inside an async endpoint.

The shapes are deliberately cross-cutting (correlation, rate budget, API
key, token→actor→verified-request) — the same shapes topics 23–25 build
for real.
"""

from typing import Annotated, Final

from fastapi import Depends

from guide.domain.demos.dep_matrix import (
    ApiKeyIssuer,
    AuthenticatedActor,
    Correlation,
    Cursor,
    ParsedToken,
    RateBudget,
    ThreadView,
    VerifiedRequest,
)


def get_correlation() -> Correlation:
    """Plain function dependency: asked once, cached for the whole request."""
    return Correlation()


def get_rate_budget() -> RateBudget:
    """Cached-x2 flavor: two handler parameters depend on this one callable."""
    return RateBudget()


def open_cursor() -> Cursor:
    """Uncached flavor: paired with ``use_cache=False`` — every ask re-runs."""
    return Cursor()


def get_parsed_token() -> ParsedToken:
    """Chain base: no dependencies of its own."""
    return ParsedToken()


def get_authenticated_actor(
    token: Annotated[ParsedToken, Depends(get_parsed_token)],
) -> AuthenticatedActor:
    """Chain middle: resolves the base itself — FastAPI solves sub-dependencies."""
    return AuthenticatedActor(token)


def get_verified_request(
    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
) -> VerifiedRequest:
    """Chain top: depth 3 — this resolved through actor, actor through token."""
    return VerifiedRequest(actor)


def peek_threadpool() -> ThreadView:
    """Sync provider inside an async endpoint: runs in the threadpool, measurably."""
    return ThreadView()


api_key_issuer: Final = ApiKeyIssuer("matrix")
"""The callable-class provider: an INSTANCE — Depends calls it, not the class."""
