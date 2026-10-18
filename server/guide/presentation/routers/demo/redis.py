"""Redis demos: topic 20's live playground (area ``redis``).

Thin router (family invariant). ``GET /playground`` walks the FIVE core
structures on the live Redis through the ``RedisPlaygroundRunner`` port the
composition root wires (string with the atomic INCR counter, hash, list,
set, sorted set — each with its real read-back), proves TTL expiry honestly
(SET with an inline EX, the TTL clock, the key's absence after the
bounded wait), and
performs a real pub/sub round-trip with both sides reported. ``?tag=`` weaves
a caller value into the keys and values so repeat calls show fresh state;
with Redis down the endpoint degrades to the service_unavailable envelope.
The router only orchestrates: parse input → one port call → one pure builder.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from guide.core.errors import AppError, FailureKind
from guide.domain.db.ports import RedisPlaygroundRunner
from guide.domain.demos.redis_playground import (
    RedisPlaygroundPayload,
    build_redis_playground_payload,
)

router = APIRouter(prefix="/api/demo/redis", tags=["demo:redis"])

DEFAULT_REDIS_TAG = "demo"
"""The playground's default caller value — woven into keys and values."""

REDIS_TAG_PATTERN = r"^[a-z0-9-]+$"
"""Tags are lowercase kebab slugs; every tag gets its own key family."""


def get_redis_playground(request: Request) -> RedisPlaygroundRunner:
    """FastAPI dependency: the playground runner (wired in create_app)."""
    runner = request.app.state.redis_playground
    if not isinstance(runner, RedisPlaygroundRunner):
        raise AppError(FailureKind.INTERNAL, "Redis playground runner not wired on app.state")
    return runner


@router.get(
    "/playground",
    response_model=RedisPlaygroundPayload,
    response_model_exclude_none=True,
)
async def read_redis_playground(
    runner: Annotated[RedisPlaygroundRunner, Depends(get_redis_playground)],
    tag: Annotated[
        str, Query(min_length=1, max_length=24, pattern=REDIS_TAG_PATTERN)
    ] = DEFAULT_REDIS_TAG,
) -> RedisPlaygroundPayload:
    """The whole scripted playground against the live Redis: five structures
    with real results, an honest TTL expiry proof, and a real pub/sub
    round-trip — the tag names the key family, so repeats are fresh."""
    run = await runner.run_playground(tag)
    return build_redis_playground_payload(run, tag)
