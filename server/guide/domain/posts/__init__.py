"""The posts domain area: entity vocabulary, the persistence port, use cases.

Phase 5's real in-repo resource — ``/api/posts`` (topic 11 and the topics
after it teach API design against this substrate). Dependency rule: the
presentation routers import the use cases, the use cases import the port,
and only the composition root (``create_app``) decides WHICH adapter
satisfies the port (currently ``guide.data.posts.InMemoryPostRepository``).
"""
