"""Dependency demo API: the span lifecycle + the dependency matrix.

Thin routers (family invariant). ``/lifecycle`` is the yield-dependency
demo: the real ``open_request_span`` dependency wraps the handler, which
answers with what it CAN know (span facts — the teardown provably has not
run yet, ``pendingEvents`` says so) and returns a ``SpanResponse`` that
stamps the send moment; ``/lifecycle/log`` serves the shared span log's
bounded ring, where the full ordering — setup → handler → response →
teardown — shows up as data. ``/matrix`` resolves every dependency flavor
in one request; the signature IS the resolution, and the pure builder in
``guide.domain.demos.dep_matrix`` derives the identity proofs.
"""

import threading
from typing import Annotated

from fastapi import APIRouter, Depends

from guide.domain.demos.dep_lifecycle import DepLifecyclePayload, build_lifecycle_payload
from guide.domain.demos.dep_matrix import (
    ApiKey,
    AuthenticatedActor,
    Correlation,
    Cursor,
    DepMatrixPayload,
    RateBudget,
    ThreadView,
    VerifiedRequest,
    build_matrix_payload,
)
from guide.presentation.dependencies.demo_flavors import (
    api_key_issuer,
    get_authenticated_actor,
    get_correlation,
    get_rate_budget,
    get_verified_request,
    open_cursor,
    peek_threadpool,
)
from guide.presentation.dependencies.request_span import (
    RequestSpanDep,
    SpanLogDep,
    SpanLogSnapshot,
    SpanResponse,
)

router = APIRouter(prefix="/api/demo/dep", tags=["demo:dep"])


@router.get("/lifecycle", response_model=DepLifecyclePayload)
async def run_lifecycle(span: RequestSpanDep) -> SpanResponse:
    """One wrapped request: record the handler beat, answer with span facts."""
    span.record("handler")
    payload = build_lifecycle_payload(
        span_id=span.span_id,
        setup_at=span.opened_at,
        handler_offset_ms=span.elapsed_ms(),
    )
    # A Response return bypasses response_model serialization — SpanResponse
    # builds the body from the payload model itself and stamps the send moment.
    return SpanResponse(span, payload)


@router.get("/lifecycle/log", response_model=SpanLogSnapshot)
async def read_lifecycle_log(log: SpanLogDep) -> SpanLogSnapshot:
    """Serve the bounded span ring — the ordering proof, as data."""
    return SpanLogSnapshot(capacity=log.capacity, events=log.tail())


@router.get("/matrix", response_model=DepMatrixPayload)
async def read_dep_matrix(
    correlation: Annotated[Correlation, Depends(get_correlation)],
    budget_a: Annotated[RateBudget, Depends(get_rate_budget)],
    budget_b: Annotated[RateBudget, Depends(get_rate_budget)],
    cursor_a: Annotated[Cursor, Depends(open_cursor, use_cache=False)],
    cursor_b: Annotated[Cursor, Depends(open_cursor, use_cache=False)],
    verified: Annotated[VerifiedRequest, Depends(get_verified_request)],
    actor_direct: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    api_key: Annotated[ApiKey, Depends(api_key_issuer)],
    thread_view: Annotated[ThreadView, Depends(peek_threadpool)],
) -> DepMatrixPayload:
    """Resolve the whole dependency matrix in one request; report identity proofs."""
    return build_matrix_payload(
        correlation=correlation,
        budget_a=budget_a,
        budget_b=budget_b,
        cursor_a=cursor_a,
        cursor_b=cursor_b,
        verified=verified,
        actor_direct=actor_direct,
        api_key=api_key,
        thread_view=thread_view,
        handler_thread=threading.current_thread().name,
    )
