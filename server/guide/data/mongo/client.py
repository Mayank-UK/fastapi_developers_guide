"""The motor client factory: one config rail, one client, lazy connect.

Mirrors ``guide.data.db.engine`` for the document store: every Mongo-
touching adapter shares clients built here, so timeout policy lives in
exactly one place. Clients are lazy — construction connects to nothing,
which keeps ``create_app()`` cheap in tests and lets the app boot with
MongoDB down (the optional-service discipline: the first OPERATION is
what pays the server-selection timeout, and failures degrade to the
``service_unavailable`` envelope).

The event-loop fine print (measured, not folklore): motor pins its loop
lazily — at the FIRST operation, not at construction — so building one
client per app in the composition root is safe under uvicorn (first
request pins the serving loop) and under per-test apps (each app's
client pins that test's loop). Sharing ONE client across event loops
is the error; per-app clients never do.
"""

from typing import Any, Final

from motor.motor_asyncio import AsyncIOMotorClient

from guide.core.config import AppConfig

SERVER_SELECTION_TIMEOUT_MS: Final = 2_000
"""How long an operation waits for a reachable mongod before failing.

Short on purpose: when MongoDB is down, a demo request should degrade
to the 503 envelope in about two seconds, not hang a worker for the
30-second driver default.
"""

CONNECT_TIMEOUT_MS: Final = 2_000
"""Per-connection handshake timeout — the other half of fast degradation."""


def create_mongo_client(config: AppConfig) -> AsyncIOMotorClient[dict[str, Any]]:
    """Build the process's motor client from the app config's URL rail.

    ``serverSelectionTimeoutMS`` bounds how long any operation spends
    hunting for a usable server when the URL points at nothing; the
    default URL rail (``FDG_MONGO_URL``) resolves inside compose, on the
    host, and in tests without changes.
    """
    return AsyncIOMotorClient(
        config.mongo_url,
        serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,
        connectTimeoutMS=CONNECT_TIMEOUT_MS,
    )
