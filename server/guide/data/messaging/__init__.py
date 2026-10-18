"""The messaging data layer: the redis stream adapter + the PG outbox.

Two adapters, two stores, one pattern: ``RedisStreams`` owns every
redis-py stream/group/set command behind the domain's producer, consumer
and processed-set ports (over the shared lazy client, 2-second socket
timeouts, ``guide_demo:msg:*`` namespace only); ``PgOutboxStore`` owns
the outbox table in PostgreSQL behind the ``OutboxAccess`` port —
including the one-transaction business write that is the pattern's
point. Both degrade to the ``service_unavailable`` envelope when their
store is down; routers never see either vocabulary.
"""

from guide.data.messaging.outbox_store import PgOutboxStore
from guide.data.messaging.redis_streams import RedisStreams

__all__ = ["PgOutboxStore", "RedisStreams"]
