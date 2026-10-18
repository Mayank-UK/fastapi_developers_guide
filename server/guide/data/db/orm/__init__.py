"""The ORM layer (topic 18): models, sessions, instrumentation, the probe.

The package's position in one line: the ORM does not OWN the schema.
Topic 16's Core ``Table`` objects — and the Alembic chain diffed against
them — stay the single source of truth for every column and constraint;
the classes in ``models`` are mapped ONTO those same tables, so nothing
is defined twice. What the mapping adds is the machinery Core
deliberately lacks: typed objects, relationships with load strategies,
a session with an identity map and dirty checking, and optimistic
versioning. ``sessions`` builds the async unit-of-work factory beside
the engine, ``query_counter`` instruments the engine so teaching claims
about emitted SQL are measurements, and ``probe`` is the adapter behind
the topic's demo.
"""

from guide.data.db.orm.models import Author, Base, Comment, Post
from guide.data.db.orm.probe import OrmProbeRepository
from guide.data.db.orm.query_counter import record_sql
from guide.data.db.orm.sessions import create_session_factory

__all__ = [
    "Author",
    "Base",
    "Comment",
    "OrmProbeRepository",
    "Post",
    "create_session_factory",
    "record_sql",
]
