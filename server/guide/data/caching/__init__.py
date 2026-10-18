"""The caching data layer: the redis-backed ``CacheStore`` adapter.

The adapter is deliberately thin — the port already IS redis-shaped — so
everything it owns is the discipline around it: the shared
``guide_demo:caching:*`` namespace (keys arrive fully formed from the
domain service, which is the single place the key is spelled), the
optional-service failure mapping (RedisError becomes the
``service_unavailable`` envelope, never a hang — the client factory's
2-second socket timeouts bound every round trip here), and redis-py's
TTL conventions translated to the port's honest ``int | None``.
"""

from guide.data.caching.redis_store import RedisCacheStore

__all__ = ["RedisCacheStore"]
