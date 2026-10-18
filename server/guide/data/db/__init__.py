"""Database adapters: the Phase 6 data layer for PostgreSQL.

One package owns every SQLAlchemy/asyncpg concern: the async engine
factory (``engine``), the Core table definitions that mirror the
migrations (``schema``), live-schema introspection for the explorer
demo (``introspection``), the in-transaction audit writer
(``audit``), and the tolerant startup migration (``lifecycle``).
Domain code depends on none of this — it speaks the ports in
``guide.domain.db``.
"""
