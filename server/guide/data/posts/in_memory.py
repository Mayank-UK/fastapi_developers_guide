"""InMemoryPostRepository: the posts port's in-memory adapter, seeded.

The first real adapter in the guide (the data layer's opening move): a
plain dict keyed by slug id, seeded with twelve deterministic posts — three
authors, overlapping tags, nine published and three drafts, fixed
timestamps one day apart — so pagination, filtering, and sorting behave
identically in every test and on every restart of the live stack. Created
posts stamp ``datetime.now`` and sort newest-first ahead of the September
seeds; the seeds themselves never move.

Identifier strategy is the adapter's to own: ids are slugs derived from
the title (lowercase, whitespace to hyphens, punctuation dropped),
uniquified with a ``-2``/``-3``… suffix when the title collides with an
existing id. Listing filters are exact matches and the default order is
newest-first with the id as tie-breaker, so equal timestamps stay
deterministic. Every method returns frozen snapshots; replace builds a NEW
``Post`` and stores it, never mutates one in place.
"""

from datetime import UTC, datetime
from typing import Final, NamedTuple

from guide.domain.posts.entities import Post, PostCreate, PostListQuery, PostPage
from guide.domain.posts.pagination import page_count


class _SeedPost(NamedTuple):
    """One deterministic seed record: draft + id + fixed timestamp."""

    post_id: str
    created_at: str
    draft: PostCreate


SEED_POSTS: Final[tuple[_SeedPost, ...]] = (
    _SeedPost(
        post_id="designing-urls-people-can-read",
        created_at="2026-09-01T08:00:00.000+00:00",
        draft=PostCreate(
            title="Designing URLs people can read",
            body="A URL is part of the interface: nouns for resources, "
            "query parameters for the view you want of them.",
            author="grace",
            tags=["design", "http"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="status-codes-are-a-contract",
        created_at="2026-09-02T08:00:00.000+00:00",
        draft=PostCreate(
            title="Status codes are a contract",
            body="200 means the answer is the representation; 201 means it "
            "created one and Location names it. Clients are allowed to "
            "depend on that.",
            author="grace",
            tags=["http", "design"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="idempotency-retold",
        created_at="2026-09-03T08:00:00.000+00:00",
        draft=PostCreate(
            title="Idempotency, retold",
            body="PUT and DELETE are idempotent; POST is not. Retry logic "
            "is written against that promise.",
            author="alan",
            tags=["http"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="content-negotiation-in-practice",
        created_at="2026-09-04T08:00:00.000+00:00",
        draft=PostCreate(
            title="Content negotiation in practice",
            body="One resource, several representations; the Accept header "
            "is a preference, the response's content-type is the fact.",
            author="alan",
            tags=["http", "design"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="why-pagination-is-a-resource-problem",
        created_at="2026-09-05T08:00:00.000+00:00",
        draft=PostCreate(
            title="Why pagination is a resource problem",
            body="A collection that returns everything is a resource with "
            "no shape: page it, count it, and link to the neighbors.",
            author="barbara",
            tags=["design", "api"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="filtering-without-surprises",
        created_at="2026-09-06T08:00:00.000+00:00",
        draft=PostCreate(
            title="Filtering without surprises",
            body="Exact-match filters with closed vocabularies beat clever "
            "matching; a filter a client cannot predict is a bug.",
            author="barbara",
            tags=["api"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="the-envelope-is-the-error-model",
        created_at="2026-09-07T08:00:00.000+00:00",
        draft=PostCreate(
            title="The envelope is the error model",
            body="One error shape for every failure means clients write "
            "error handling once — per-endpoint error bodies never "
            "survive contact with a second team.",
            author="grace",
            tags=["api", "design"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="versioning-an-api-you-already-shipped",
        created_at="2026-09-08T08:00:00.000+00:00",
        draft=PostCreate(
            title="Versioning an API you already shipped",
            body="Breaking changes need a version boundary clients can "
            "see; everything else should ship without one.",
            author="alan",
            tags=["api"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="notes-on-rfc-9457",
        created_at="2026-09-09T08:00:00.000+00:00",
        draft=PostCreate(
            title="Notes on RFC 9457",
            body="Problem details give errors a standard vocabulary: type, "
            "title, status, detail, instance. Borrow the shape, keep the "
            "envelope consistent.",
            author="barbara",
            tags=["http", "api"],
            status="published",
        ),
    ),
    _SeedPost(
        post_id="drafting-the-webhooks-chapter",
        created_at="2026-09-10T08:00:00.000+00:00",
        draft=PostCreate(
            title="Drafting the webhooks chapter",
            body="Reversed APIs: now we call the client. Signatures, "
            "retries, and dead letters — still a status code story.",
            author="grace",
            tags=["drafts"],
            status="draft",
        ),
    ),
    _SeedPost(
        post_id="drafting-the-graphql-chapter",
        created_at="2026-09-11T08:00:00.000+00:00",
        draft=PostCreate(
            title="Drafting the GraphQL chapter",
            body="One endpoint, a typed query language, and resolvers that "
            "look a lot like the use cases this guide already builds.",
            author="alan",
            tags=["drafts"],
            status="draft",
        ),
    ),
    _SeedPost(
        post_id="drafting-the-grpc-chapter",
        created_at="2026-09-12T08:00:00.000+00:00",
        draft=PostCreate(
            title="Drafting the gRPC chapter",
            body="Contracts from .proto files, four streaming shapes, and "
            "deadlines as first-class citizens.",
            author="barbara",
            tags=["drafts"],
            status="draft",
        ),
    ),
)
"""Twelve deterministic posts — the substrate's curriculum-authored seed."""


def _slugify(title: str) -> str:
    """Derive a slug from a title: lowercase, hyphen-separated, alphanumeric."""
    words = "-".join(title.lower().split())
    kept = "".join(
        character if character.isalnum() or character == "-" else "" for character in words
    )
    return "-".join(part for part in kept.split("-") if part) or "post"


def _matches(post: Post, query: PostListQuery) -> bool:
    """Exact-match filters: author, tag membership, status."""
    if query.author is not None and post.author != query.author:
        return False
    if query.tag is not None and query.tag not in post.tags:
        return False
    if query.status is not None and post.status != query.status:
        return False
    return True


def _ordered(posts: list[Post], sort: str) -> list[Post]:
    """Apply the sort vocabulary; the id is always the final tie-breaker."""
    if sort == "oldest":
        return sorted(posts, key=lambda post: (post.created_at, post.id))
    if sort == "title":
        return sorted(posts, key=lambda post: (post.title, post.id))
    return sorted(posts, key=lambda post: (post.created_at, post.id), reverse=True)


class InMemoryPostRepository:
    """In-memory posts: seeded, per-app, deliberately unpersisted.

    Implements the ``PostRepository`` port without inheriting from it —
    structural typing is the point of a Protocol (ruff/mypy verify the
    match in ``tests/data/test_in_memory_posts.py``).
    """

    def __init__(self, seed: bool = True) -> None:
        """Start empty or with the fixed twelve-post seed."""
        self._posts: dict[str, Post] = {}
        if seed:
            for seed_post in SEED_POSTS:
                self._posts[seed_post.post_id] = Post(
                    id=seed_post.post_id,
                    **seed_post.draft.model_dump(),
                    created_at=seed_post.created_at,
                    updated_at=seed_post.created_at,
                )

    def _unique_slug(self, base: str) -> str:
        """Suffix -2, -3, … until the slug is free (titles may collide)."""
        if base not in self._posts:
            return base
        suffix = 2
        while f"{base}-{suffix}" in self._posts:
            suffix += 1
        return f"{base}-{suffix}"

    def list(self, query: PostListQuery) -> PostPage:
        """Filter, sort, count, slice — totals reflect the filters."""
        selected = [post for post in self._posts.values() if _matches(post, query)]
        ordered = _ordered(selected, query.sort)
        total = len(ordered)
        start = (query.page - 1) * query.limit
        return PostPage(
            items=ordered[start : start + query.limit],
            total=total,
            page=query.page,
            limit=query.limit,
            pages=page_count(total, query.limit),
        )

    def get(self, post_id: str) -> Post | None:
        """One post, or None when the id is unknown."""
        return self._posts.get(post_id)

    def create(self, draft: PostCreate) -> Post:
        """Mint a unique slug, stamp now as created and updated, store."""
        now = datetime.now(UTC).isoformat(timespec="milliseconds")
        post_id = self._unique_slug(_slugify(draft.title))
        post = Post(
            id=post_id,
            **draft.model_dump(),
            created_at=now,
            updated_at=now,
        )
        self._posts[post_id] = post
        return post

    def replace(self, post_id: str, draft: PostCreate) -> Post | None:
        """Replace content wholesale; keep id and created_at; bump updated_at."""
        current = self._posts.get(post_id)
        if current is None:
            return None
        replaced = Post(
            id=current.id,
            **draft.model_dump(),
            created_at=current.created_at,
            updated_at=datetime.now(UTC).isoformat(timespec="milliseconds"),
        )
        self._posts[post_id] = replaced
        return replaced
