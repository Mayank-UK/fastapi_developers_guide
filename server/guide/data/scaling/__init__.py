"""The scaling data layer: the redis-backed ``SharedCounterStore`` adapter.

The adapter is deliberately tiny — the port already IS redis-shaped — so
everything it owns is the discipline around it: the shared
``guide_demo:scaling:*`` namespace (the demo's one key, spelled by the
domain builder), and the optional-service failure mapping (RedisError
becomes the ``service_unavailable`` envelope, never a hang — the client
factory's 2-second socket timeouts bound every round trip here).
"""

from guide.data.scaling.redis_counter import RedisSharedCounter

__all__ = ["RedisSharedCounter"]
