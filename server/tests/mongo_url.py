"""Shared constant: the dev compose MongoDB URL for integration tests.

Topic 19's integration tests run against the REAL dev-stack MongoDB
(the compose service named ``mongo``), through the app's own config
rail — the same stack-up run posture the PostgreSQL tests use (see
``pg_url``). The demos own the ``guide_demo`` database exclusively;
nothing pre-existing in the container is ever touched.
"""

COMPOSE_MONGO_URL = "mongodb://mongo:27017"
