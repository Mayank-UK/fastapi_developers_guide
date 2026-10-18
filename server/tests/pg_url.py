"""Shared constant: the dev compose PostgreSQL URL for integration tests.

Topic 16's integration tests run against the REAL dev-stack PostgreSQL
(the compose service named ``postgres``), through the app's own config
rail — Testcontainers wiring arrives with topic 18 and is deliberately
not preempted here. The stack-up run posture (agentic_development.md)
makes this URL resolvable wherever the suite runs.
"""

COMPOSE_PG_URL = "postgresql+asyncpg://postgres:guide@postgres:5432/guide"
