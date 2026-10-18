"""The caching-lab demo payloads: the state panel's facts, derived purely.

``GET /api/demo/caching/lab`` serves this payload — topic 21's single
demo (``caching:lab``), inline in the section that teaches cache-aside.
The lab is INTERACTIVE: its fetch button hits the REAL conditional
endpoint, its invalidate and stampede buttons POST to the two action
endpoints, and this roster payload carries the state panel's facts plus
the copy that labels the simulated origin cost honestly. The builder is
PURE — every sentence derives from the state row and the service's own
constants, so the payload can never drift from what the cache really does.
"""

from guide.core.serialization import CamelModel
from guide.domain.caching.ports import CacheStateRow
from guide.domain.caching.service import (
    NAMESPACE_DISPLAY,
    ORIGIN_COST_MS,
    ORIGIN_COST_NOTE,
    TTL_SECONDS,
)


class CachingLabPayload(CamelModel):
    """Wire shape of ``GET /api/demo/caching/lab`` — the state panel's roster."""

    namespace: str
    key: str
    ttl_seconds: int
    origin_cost_ms: int
    origin_cost_note: str
    posts_endpoint: str
    invalidate_endpoint: str
    stampede_endpoint: str
    state: CacheStateRow
    reasoning: str


def build_caching_lab_payload(
    state: CacheStateRow,
    posts_endpoint: str,
    invalidate_endpoint: str,
    stampede_endpoint: str,
) -> CachingLabPayload:
    """Shape the lab roster (pure) — the reasoning derives from the state.

    The endpoint paths arrive as parameters because they are presentation
    facts (the router owns its own paths); everything else comes from the
    domain's own constants, quoted live.
    """
    liveness = (
        f"an entry is live for up to {state.ttl_seconds} s (TTL {state.ttl_remaining_s} s "
        f"remaining) and serves hits without touching the origin"
        if state.present and state.ttl_remaining_s is not None
        else f"no entry is live — the next {posts_endpoint} is a miss and pays the origin"
    )
    telemetry = state.telemetry
    reasoning = (
        f"One key ({state.key}) caches the newest-posts page as its canonical JSON "
        f"string, written with a {TTL_SECONDS} s TTL the moment an origin fill lands. "
        f"{liveness}. Origin cost is {ORIGIN_COST_NOTE}; the caching around it — "
        f"keys, TTL, invalidation, single-flight, these counters (hits "
        f"{telemetry.hits}, misses {telemetry.misses}, coalesced {telemetry.coalesced}, "
        f"invalidations {telemetry.invalidations}) — is real. "
        f"Fetch {posts_endpoint} twice to watch miss become hit, send its ETag back "
        f"as If-None-Match for a 304, POST {invalidate_endpoint} to force a refill, "
        f"or POST {stampede_endpoint} to watch single-flight collapse a cold stampede "
        f"into exactly one origin fetch."
    )
    return CachingLabPayload(
        namespace=NAMESPACE_DISPLAY,
        key=state.key,
        ttl_seconds=TTL_SECONDS,
        origin_cost_ms=ORIGIN_COST_MS,
        origin_cost_note=ORIGIN_COST_NOTE,
        posts_endpoint=posts_endpoint,
        invalidate_endpoint=invalidate_endpoint,
        stampede_endpoint=stampede_endpoint,
        state=state,
        reasoning=reasoning,
    )
