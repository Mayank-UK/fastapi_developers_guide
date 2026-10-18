"""The posts persistence port: a Protocol the adapters implement.

``PostRepository`` is the boundary the use cases depend on — they never
learn WHICH store answers (in-memory today, a database from Phase 6 on).
``@runtime_checkable`` exists for exactly one wiring check: the FastAPI
dependency that resolves the use cases off ``app.state`` can verify the
composition root actually wired a PostRepository-shaped bundle, mirroring
how ``get_note_store`` guards its store.
"""

from typing import Protocol, runtime_checkable

from guide.domain.posts.entities import Post, PostCreate, PostListQuery, PostPage


@runtime_checkable
class PostRepository(Protocol):
    """What every posts adapter must do; returns snapshots, never live state."""

    def list(self, query: PostListQuery) -> PostPage:
        """One filtered, sorted, paginated page of posts."""
        ...

    def get(self, post_id: str) -> Post | None:
        """One post, or None when the id is unknown."""
        ...

    def create(self, draft: PostCreate) -> Post:
        """Mint an id, stamp the clock, store the snapshot, return it."""
        ...

    def replace(self, post_id: str, draft: PostCreate) -> Post | None:
        """Full-replace content; keep id and created_at; refresh updated_at.

        Returns None when the id is unknown — the caller decides that means
        404 (existence is a domain answer, topic 10's edge-vs-domain line).
        """
        ...
