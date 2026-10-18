"""The MongoDB data layer: motor client factory + the console adapter.

Mirrors ``guide.data.db`` for the document store — adapters here own
every motor/pymongo import in the guide; the domain port (``MongoConsoleRunner``
in ``guide.domain.db.ports``) speaks plain result rows, and unreachable
MongoDB degrades to the ``service_unavailable`` envelope.
"""

from guide.data.mongo.client import create_mongo_client
from guide.data.mongo.console import MongoConsoleRepository

__all__ = ["MongoConsoleRepository", "create_mongo_client"]
