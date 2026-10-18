"""The demo comment ledger: the second owned resource, seeded and small.

Posts have their own substrate; comments deserve one too, because
moderation is the demo's admin-only action and it needs a REAL object
to moderate. The ledger is deliberately tiny and in-domain — three
seeded comments on seeded posts, authored by the same principals the
role registry knows, held in per-app state exactly like the reqres note
store: no port, no adapter, no database, copy-on-write snapshots. The
moderation operation is a status flip (visible ⇄ hidden) stamped with
the moderator's name — the whole honest surface a teaching ledger needs.
"""

from typing import Final, Literal

from guide.core.serialization import CamelModel

CommentStatus = Literal["visible", "hidden"]
"""A comment's two states; moderation flips between them."""

MODERATION_TARGETS: Final[tuple[str, ...]] = ("visible", "hidden")
"""The closed moderation vocabulary — anything else dies at the edge."""


class DemoComment(CamelModel):
    """One seeded comment: what it says, where it sits, who owns it.

    ``author`` is the ownership handle — the same namespace as post
    authors and principal names, which is the entire point.
    """

    id: str
    post_id: str
    author: str
    body: str
    status: CommentStatus
    moderated_by: str | None


SEED_COMMENTS: Final[tuple[DemoComment, ...]] = (
    DemoComment(
        id="urls-are-for-machines",
        post_id="designing-urls-people-can-read",
        author="alan",
        body="URLs are for machines — readability is a pleasant coincidence.",
        status="visible",
        moderated_by=None,
    ),
    DemoComment(
        id="envelope-skeptic",
        post_id="status-codes-are-a-contract",
        author="barbara",
        body="Every team that ignored the envelope wrote their own worse one.",
        status="visible",
        moderated_by=None,
    ),
    DemoComment(
        id="retry-this",
        post_id="idempotency-retold",
        author="grace",
        body="Retrying this comment is safe — that is the whole lesson.",
        status="visible",
        moderated_by=None,
    ),
)
"""Three deterministic comments on three seeded posts — moderation's targets."""


class CommentLedger:
    """Per-app, in-memory, copy-on-write: list, find, moderate."""

    def __init__(self, seed: bool = True) -> None:
        """Start with the fixed three-comment seed, or empty for tests."""
        self._comments: dict[str, DemoComment] = (
            {comment.id: comment for comment in SEED_COMMENTS} if seed else {}
        )

    def list(self) -> list[DemoComment]:
        """Every comment, seed order — the panel's roster."""
        return [self._comments[comment_id] for comment_id in sorted(self._comments)]

    def find(self, comment_id: str) -> DemoComment | None:
        """One comment, or None — the router maps that to the 404 envelope."""
        return self._comments.get(comment_id)

    def moderate(
        self, comment_id: str, status: CommentStatus, moderator: str
    ) -> DemoComment | None:
        """Flip a comment's status and stamp the moderator — or None if unknown."""
        current = self._comments.get(comment_id)
        if current is None:
            return None
        updated = current.model_copy(
            update={"status": status, "moderated_by": moderator}
        )
        self._comments[comment_id] = updated
        return updated
