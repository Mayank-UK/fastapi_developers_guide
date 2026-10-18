"""Data-layer anchor for the posts area; the in-memory adapter lives here.

From Phase 6 on, database adapters (SQLAlchemy against PostgreSQL) join
this package and the composition root picks between them — the port in
``guide.domain.posts.ports`` is the seam that makes the swap one line.
"""
