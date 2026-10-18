"""Shared constant: the dev compose Redis URL for integration tests.

Topic 20's integration tests run against the REAL dev-stack Redis (the
compose service named ``redis``), through the app's own config rail — the
same stack-up run posture the PostgreSQL and MongoDB tests use (see
``pg_url`` and ``mongo_url``). The demos own the ``guide_demo:redis:*`` key
namespace exclusively; nothing pre-existing in the container is ever touched.
"""

COMPOSE_REDIS_URL = "redis://redis:6379"
