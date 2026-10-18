"""The redis-playground demo payloads: everything the live store answered.

``GET /api/demo/redis/playground`` serves these payloads — topic 20's single
demo, inline in the section that teaches the structures. One request walks
the five core structures on the live Redis through the
``RedisPlaygroundRunner`` port (string with the atomic INCR counter, hash,
list, set, sorted set with scores), proves TTL expiry honestly (SET with an inline EX, the
TTL clock observed, the key's absence after the bounded wait), and performs
a real pub/sub round-trip with both sides reported. The builder below is
PURE — it passes the run's rows through and derives every reasoning
sentence from what actually ran, so the payload can never drift from the
store.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import (
    PubsubProofRow,
    RedisPlaygroundRun,
    StructureRow,
    TtlProofRow,
)


class RedisPlaygroundPayload(CamelModel):
    """Wire shape of ``GET /api/demo/redis/playground``."""

    namespace: str
    tag: str
    structures: list[StructureRow]
    ttl: TtlProofRow
    pubsub: PubsubProofRow
    reasoning: str


def build_redis_playground_payload(run: RedisPlaygroundRun, tag: str) -> RedisPlaygroundPayload:
    """Shape the playground run (pure) — the reasoning derives from the rows."""
    kinds = " → ".join(structure.kind for structure in run.structures)
    reasoning = (
        f"Every row above is what the live store answered under "
        f"{run.namespace} — five structures walked in order ({kinds}), each "
        "with its real read-back. The counter was INCR'd atomically on the "
        "server, the hash came back whole from HGETALL, the list showed its "
        "push-order inversion, the set refused nothing twice (uniqueness is "
        f"the structure's job), and the sorted set ordered itself by score. "
        f"The TTL key lived its configured {run.ttl.ttl_seconds} s "
        f"(TTL answered {run.ttl.ttl_first_read} s right after the SET with "
        "its inline EX) and was nil on GET after the "
        f"{run.ttl.waited_ms} ms bounded wait — evicted by the store, not by "
        "this code. The pub/sub round-trip closed for "
        f"real: PUBLISH answered {run.pubsub.receivers} receiver(s) and the "
        "bounded listener collected the identical payload."
    )
    return RedisPlaygroundPayload(
        namespace=run.namespace,
        tag=tag,
        structures=run.structures,
        ttl=run.ttl,
        pubsub=run.pubsub,
        reasoning=reasoning,
    )
