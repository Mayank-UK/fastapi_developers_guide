"""Pure builders of the dependency demos: identity tokens + verdict logic.

The endpoint tests measure the framework through the real app; these pin
the builders' own logic on crafted inputs — token derivation, both branches
of every derived verdict, and the lifecycle payload's honest shape.
"""

import threading

from guide.domain.demos.dep_lifecycle import build_lifecycle_payload
from guide.domain.demos.dep_matrix import (
    ApiKeyIssuer,
    AuthenticatedActor,
    Correlation,
    Cursor,
    DepMatrixPayload,
    ParsedToken,
    RateBudget,
    ThreadView,
    VerifiedRequest,
    build_matrix_payload,
    identity_token,
)


def a_matrix(
    *,
    budget_a: RateBudget | None = None,
    budget_b: RateBudget | None = None,
    cursor_a: Cursor | None = None,
    cursor_b: Cursor | None = None,
    actor_direct: AuthenticatedActor | None = None,
    handler_thread: str = "irrelevant",
) -> DepMatrixPayload:
    """One crafted matrix call: shared objects test 'same', fresh pairs 'distinct'."""
    base = ParsedToken()
    actor = AuthenticatedActor(base)
    return build_matrix_payload(
        correlation=Correlation(),
        budget_a=budget_a if budget_a is not None else RateBudget(),
        budget_b=budget_b if budget_b is not None else RateBudget(),
        cursor_a=cursor_a if cursor_a is not None else Cursor(),
        cursor_b=cursor_b if cursor_b is not None else Cursor(),
        verified=VerifiedRequest(actor),
        actor_direct=actor_direct if actor_direct is not None else actor,
        api_key=ApiKeyIssuer("test")(),
        thread_view=ThreadView(),
        handler_thread=handler_thread,
    )


def test_identity_token_names_the_class_and_separates_instances() -> None:
    first, second = Correlation(), Correlation()
    assert identity_token(first).startswith("Correlation#")
    assert identity_token(first) == identity_token(first)
    assert identity_token(first) != identity_token(second)


def test_cached_row_reports_same_instance_only_for_one_object() -> None:
    shared = RateBudget()
    same = a_matrix(budget_a=shared, budget_b=shared)
    assert same.rows[2].verdict == "same-instance"
    distinct = a_matrix()  # two fresh RateBudget instances
    assert distinct.rows[2].verdict == "distinct-instances"


def test_uncached_row_reports_distinct_instances_only_for_two_objects() -> None:
    cursor = Cursor()
    same = a_matrix(cursor_a=cursor, cursor_b=cursor)
    assert same.rows[3].verdict == "same-instance"
    distinct = a_matrix()
    assert distinct.rows[3].verdict == "distinct-instances"


def test_chain_row_shares_the_middle_only_with_the_same_actor() -> None:
    shared = a_matrix()
    assert shared.rows[4].verdict == "shared-middle"
    tokens = shared.rows[4].tokens
    assert tokens[1] == tokens[3]

    other = a_matrix(actor_direct=AuthenticatedActor(ParsedToken()))
    assert other.rows[4].verdict == "distinct-instances"


def test_sync_row_derives_the_threadpool_verdict_from_thread_names() -> None:
    here = threading.current_thread().name
    same_thread = a_matrix(handler_thread=here)
    assert same_thread.rows[5].verdict == "event-loop"
    other_thread = a_matrix(handler_thread="not-" + here)
    assert other_thread.rows[5].verdict == "threadpool"
    assert other_thread.rows[5].tokens == [
        f"dep-thread:{here}",
        "handler-thread:not-" + here,
    ]


def test_lifecycle_payload_confesses_its_pending_teardown() -> None:
    payload = build_lifecycle_payload(
        span_id="abc123def456", setup_at="2026-10-15T00:00:00.000+00:00", handler_offset_ms=3
    )
    assert payload.span_id == "abc123def456"
    assert payload.pending_events == ["teardown"]
    payload.pending_events.clear()  # a copy, not the module constant
    assert build_lifecycle_payload("x", "y", 0).pending_events == ["teardown"]
