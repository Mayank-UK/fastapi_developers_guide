"""The caching domain area: cache-aside over the posts substrate, HTTP
conditionals, and the ports the redis adapter satisfies.

Topic 21's subject. ``service.py`` is the teaching artifact itself — a
cache-aside read path with double-checked, single-flight origin fills
(in-process ``asyncio.Lock`` per key) and honest telemetry; ``ports.py``
defines the ``CacheStore`` port (a thin key-value abstraction the redis
adapter implements under the optional-service discipline) and the result
rows every payload speaks; ``conditionals.py`` holds the pure HTTP
conditional-request helpers (ETag computation, ``If-None-Match`` matching)
the real conditional endpoint applies. Everything here is driver-free:
redis vocabulary never crosses into the domain.
"""
