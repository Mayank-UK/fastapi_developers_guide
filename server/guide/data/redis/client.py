"""The redis.asyncio client factory: one config rail, one client, lazy connect.

Mirrors ``guide.data.db.engine`` and ``guide.data.mongo.client`` for the
in-memory store: every Redis-touching adapter shares clients built here, so
timeout policy lives in exactly one place. ``Redis.from_url`` is lazy —
construction connects to nothing, which keeps ``create_app()`` cheap in tests
and lets the app boot with Redis down (the optional-service discipline: the
first COMMAND is what pays the connect, and failures degrade to the
``service_unavailable`` envelope instead of hanging a worker).

``decode_responses=True`` turns every reply into ``str`` at the client edge —
the adapter and its display rows never decode bytes, and the wire model speaks
strings only. Unlike motor (topic 19's measured event-loop pinning),
redis-py's asyncio client is loop-native: one client per app still holds (the
composition root wires it), but the lazily-opened connections bind the
SERVING loop by construction and no stale-pin hazard exists.
"""

from typing import Final

from redis.asyncio import Redis

from guide.core.config import AppConfig

SOCKET_CONNECT_TIMEOUT_S: Final = 2.0
"""Per-connection handshake timeout — connection-refused must be fast."""

SOCKET_TIMEOUT_S: Final = 2.0
"""Read/write timeout per command — a down Redis degrades in ~2 s, not 60.

This bound covers the pub/sub connection's reads too: the round-trip
choreography publishes immediately after subscribing, so a healthy store
delivers within milliseconds and the timeout is only ever the honest
failure path for a store that stopped answering."""


def create_redis_client(config: AppConfig) -> Redis:
    """Build the process's redis.asyncio client from the config's URL rail.

    Short socket timeouts keep the optional-service discipline FAST: when the
    URL points at nothing, the first command fails within the two-second
    bounds instead of the driver default, and the adapter maps that failure
    to the 503 envelope.
    """
    return Redis.from_url(
        config.redis_url,
        decode_responses=True,
        socket_connect_timeout=SOCKET_CONNECT_TIMEOUT_S,
        socket_timeout=SOCKET_TIMEOUT_S,
    )
