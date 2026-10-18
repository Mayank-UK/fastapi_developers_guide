"""The authentication data layer: one in-memory adapter, five ports.

``InMemoryAuthState`` satisfies every auth store Protocol on plain
dictionaries seeded with pre-hashed argon2 credentials — per-app state,
no new tables (the posts-substrate discipline), the same shape a
PostgreSQL or Redis adapter would take over. Routers never see this
module; the composition root wires it once per app.
"""

from guide.data.auth.memory import SEED_USERS, InMemoryAuthState

__all__ = ["InMemoryAuthState", "SEED_USERS"]
