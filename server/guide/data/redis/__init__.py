"""The Redis data layer: redis.asyncio client factory + the playground adapter.

Mirrors ``guide.data.db`` and ``guide.data.mongo`` for the in-memory store —
adapters here own every redis-py import in the guide; the domain port
(``RedisPlaygroundRunner`` in ``guide.domain.db.ports``) speaks plain result
rows, and unreachable Redis degrades to the ``service_unavailable`` envelope.
"""

from guide.data.redis.client import create_redis_client
from guide.data.redis.playground import RedisPlaygroundRepository

__all__ = ["RedisPlaygroundRepository", "create_redis_client"]
