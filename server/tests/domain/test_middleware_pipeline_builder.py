"""Middleware-pipeline builder: the pure engine against a fixture stack.

The builder is the demo's engine — stack composition (bookends + user
layers + router terminal), the in-memory pure-ASGI trace that proves wrap
order, and the order derivations — so these tests pin each fact against a
hand-authored stack, independent of the live app.
"""

import pytest

from guide.domain.demos.middleware_pipeline import (
    build_middleware_pipeline_payload,
    run_traced_pipeline,
)

STACK = [
    "ServerErrorMiddleware",
    "ExceptionTelemetryMiddleware",
    "RequestIdMiddleware",
    "ExceptionMiddleware",
    "AsyncExitStackMiddleware",
    "APIRouter",
]
"""The fixture stack, outermost first — mirrors this app's real chain."""


async def build(
    stack: list[str] = STACK,  # noqa: B006 — fixture default, never mutated
    user: list[str] | None = None,
    request_id: str = "probe-42",
):
    return await build_middleware_pipeline_payload(
        stack_names=stack,
        user_middleware_names=user if user is not None else ["RequestIdMiddleware"],
        request_id=request_id,
    )


async def test_stack_classifies_framework_user_and_router() -> None:
    payload = await build()
    assert [layer.name for layer in payload.stack] == STACK
    assert [layer.kind for layer in payload.stack] == [
        "framework",
        "framework",
        "user",
        "framework",
        "framework",
        "router",
    ]
    assert [layer.order_index for layer in payload.stack] == list(range(len(STACK)))


async def test_known_layers_carry_roles_and_unknown_get_generic_ones() -> None:
    payload = await build(
        stack=["ServerErrorMiddleware", "RateLimitMiddleware", "APIRouter"],
        user=["RateLimitMiddleware"],
    )
    roles = {layer.name: layer.role for layer in payload.stack}
    assert "bookend" in roles["ServerErrorMiddleware"]
    assert roles["RateLimitMiddleware"] == "user middleware registered by create_app"
    assert "terminal ASGI app" in roles["APIRouter"]


async def test_trace_descends_runs_the_handler_once_and_unwinds() -> None:
    payload = await build()
    middleware_stages = STACK[:-1]
    assert [event.phase for event in payload.trace] == ["request"] * 5 + ["handler"] + [
        "response"
    ] * 5
    assert [event.stage for event in payload.trace] == (
        middleware_stages + [STACK[-1]] + list(reversed(middleware_stages))
    )
    assert [event.sequence for event in payload.trace] == list(range(11))


async def test_orders_derive_from_the_stack_and_reverse() -> None:
    payload = await build()
    assert payload.request_side_order == STACK
    assert payload.response_side_order == list(reversed(STACK))


async def test_request_id_and_header_ride_the_payload() -> None:
    payload = await build(request_id="round-trip-7")
    assert payload.request_id == "round-trip-7"
    assert payload.request_id_header == "x-request-id"
    assert "x-request-id" in payload.reasoning
    assert "requestId field" in payload.reasoning


async def test_every_layer_note_names_its_stage() -> None:
    payload = await build()
    for event in payload.trace:
        assert event.stage in event.note


async def test_a_bare_router_stack_traces_one_handler_event() -> None:
    events = await run_traced_pipeline(["APIRouter"])
    assert [(event.stage, event.phase, event.sequence) for event in events] == [
        ("APIRouter", "handler", 0)
    ]


async def test_an_empty_stack_is_refused() -> None:
    with pytest.raises(ValueError):
        await run_traced_pipeline([])
    with pytest.raises(ValueError):
        await build(stack=[])
