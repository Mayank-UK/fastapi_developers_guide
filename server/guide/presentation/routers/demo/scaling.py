"""The statelessness demo (topic 40, area ``scaling``).

Thin router (family invariant): one GET, the payload builder does the
work, a declared response model. The panel serves the state-placement
lesson by introspection — the router snapshots the REAL in-process facts
off the composition root (the live scenario flags, the posts count via
the use case, the chat rooms, the limiter's policy: counters and flags
only, no I/O, nothing from the data layer imported here), and the builder
walks one logical request through two per-replica state worlds: a
process-local write that never crosses to the second replica, beside a
real redis INCR that does. With Redis down the endpoint degrades to the
service_unavailable envelope (the optional-service discipline).
"""

import os
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request

from guide.core.errors import AppError, FailureKind
from guide.core.scenario import ScenarioStore
from guide.domain.demos.scaling_stateless import (
    ProcessFacts,
    StatelessPanel,
    build_stateless_panel,
)
from guide.domain.posts.entities import PostListQuery
from guide.domain.posts.use_cases import PostUseCases
from guide.domain.realtime.chat import ChatRoomService
from guide.domain.scaling.ports import SharedCounterStore
from guide.domain.security.rate_limit import SlidingWindowLimiter

router = APIRouter(prefix="/api/demo/scaling", tags=["demo:scaling"])

STATELESS_PATH: Final = "/stateless"
"""The router's one path (prefix-relative) — the terminal companion names it."""


def get_shared_counter(request: Request) -> SharedCounterStore:
    """FastAPI dependency: the shared counter (wired in create_app)."""
    counter = request.app.state.shared_counter
    if not isinstance(counter, SharedCounterStore):
        raise AppError(FailureKind.INTERNAL, "Shared counter not wired on app.state")
    return counter


SharedCounterDep = Annotated[SharedCounterStore, Depends(get_shared_counter)]


def _process_facts(request: Request) -> ProcessFacts:
    """Snapshot the composition root's in-process facts — counters only, no I/O.

    Reads what ``create_app`` wired on ``app.state``: the scenario store's
    current flags, the posts use case's count (the public port, one
    in-memory call), the chat service's rooms, and the limiter's policy.
    The plain ``ProcessFacts`` record crosses into the domain builder —
    the builder never touches the app or the data layer itself.
    """
    scenario = request.app.state.scenario
    if not isinstance(scenario, ScenarioStore):
        raise AppError(FailureKind.INTERNAL, "Scenario store not wired on app.state")
    posts_use_cases = request.app.state.posts_use_cases
    if not isinstance(posts_use_cases, PostUseCases):
        raise AppError(FailureKind.INTERNAL, "Posts use cases not wired on app.state")
    chat = request.app.state.chat_service
    if not isinstance(chat, ChatRoomService):
        raise AppError(FailureKind.INTERNAL, "Chat service not wired on app.state")
    limiter = request.app.state.rate_limiter
    if not isinstance(limiter, SlidingWindowLimiter):
        raise AppError(FailureKind.INTERNAL, "Rate limiter not wired on app.state")
    listing = posts_use_cases.list_posts.execute(PostListQuery(limit=1))
    if not listing.is_ok():
        raise AppError(FailureKind.INTERNAL, "Posts count snapshot failed")
    return ProcessFacts(
        pid=os.getpid(),
        scenario=scenario.get(),
        posts_total=listing.value.total,
        chat_rooms=len(chat.manager.rooms()),
        chat_connections=chat.manager.total_connections(),
        rate_policy=(
            f"{limiter.policy.budget} hits / {limiter.policy.window_s:g}s "
            f"per {limiter.policy.keying}"
        ),
    )


ProcessFactsDep = Annotated[ProcessFacts, Depends(_process_facts)]


@router.get(STATELESS_PATH, response_model=StatelessPanel)
async def read_stateless_panel(
    counter: SharedCounterDep, process: ProcessFactsDep
) -> StatelessPanel:
    """Serve the state-placement panel: two replicas, one shared counter."""
    return await build_stateless_panel(counter=counter, process=process)
