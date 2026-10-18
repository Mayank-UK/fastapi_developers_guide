"""The real GraphQL API: strawberry's router over the posts substrate.

Topic 11 built ``/api/posts`` as a REST contract; this module mounts the
SAME domain at ``/api/graphql`` — a typed strawberry schema whose
resolvers call the SAME ``PostUseCases`` bundle the REST router resolves.
Resolvers are presentation: parse/validate input → call a use case → map
the ``Result`` to an answer — the family's thin-router invariant, carried
into GraphQL. The dependency rule is untouched (presentation → domain ←
data); the composition root in ``create_app`` still owns the wiring.

Where the posture differs, GraphQL itself differs: one URL and one verb
(POST — the query rides the body); the CLIENT names the shape of the
answer; failures ride 200 responses as ``{"errors": [...]}`` instead of
status codes (a deliberate ``not_found`` becomes a ``GraphQLError`` with
the family's code in ``extensions``); and the contract is the schema
itself — introspectable at runtime, invisible to OpenAPI (the mount is
``include_in_schema=False``: the document could only show two bare
operations with no query language in them; ``schema.as_str()`` serves the
honest SDL).

The N+1 exit lives here too: ``AuthorLoader`` batches every author
lookup a query level triggers into ONE repository round, so a page of
posts resolves its authors without one query per post.
"""

from collections import Counter
from enum import Enum
from typing import Final

import strawberry
from fastapi import Request
from graphql import GraphQLError
from pydantic import ValidationError
from strawberry.dataloader import DataLoader
from strawberry.fastapi import BaseContext, GraphQLRouter

from guide.core.errors import FailureKind
from guide.core.result import Err
from guide.domain.posts.entities import (
    DEFAULT_LIST_LIMIT,
    PostCreate,
    PostListQuery,
)
from guide.domain.posts.entities import (
    Post as DomainPost,
)
from guide.domain.posts.entities import (
    PostPage as DomainPage,
)
from guide.domain.posts.use_cases import ListPostsUseCase, PostUseCases
from guide.presentation.routers.posts import get_post_use_cases

GRAPHQL_PATH: Final[str] = "/api/graphql"
"""The one URL the whole GraphQL API lives at — queries and mutations both."""


@strawberry.enum
class PostStatus(Enum):
    """The domain's two post states, spelled as GraphQL enum values."""

    DRAFT = "draft"
    PUBLISHED = "published"


@strawberry.enum
class PostSort(Enum):
    """The domain's closed sort vocabulary; NEWEST mirrors the REST default."""

    NEWEST = "newest"
    OLDEST = "oldest"
    TITLE = "title"


@strawberry.type
class Author:
    """A byline projected with live facts: how many posts carry this name."""

    id: str
    post_count: int = strawberry.field(
        name="postCount", description="Posts in the store whose byline is this id."
    )


class AuthorLoader(DataLoader[str, Author | None]):
    """Batched author lookups: ONE repository round answers the whole batch."""

    def __init__(self, list_posts: ListPostsUseCase) -> None:
        super().__init__(load_fn=self._load_authors)
        self._list_posts = list_posts

    async def _load_authors(self, names: list[str]) -> list[Author | None]:
        """Tally one page-sized snapshot of the store; answer keys in order."""
        # load(key) registers with the current batch and returns a future;
        # while one query level resolves, every author field adds its key.
        # Only then does the loader dispatch ONE call here with the
        # collected, deduplicated names — six posts, three bylines, one
        # round. The context getter builds one loader per request, so the
        # batch and its cache live exactly as long as the query.
        result = self._list_posts.execute(PostListQuery(limit=100, sort="oldest"))
        if isinstance(result, Err):
            raise result.failure
        tally: Counter[str] = Counter(post.author for post in result.value.items)
        # An unknown byline answers None (a null author) rather than an
        # invented identity; the limit matches the substrate's collection
        # cap (100) — the same ceiling every REST list request obeys.
        return [
            Author(id=name, post_count=tally[name]) if name in tally else None
            for name in names
        ]


class GraphQLContext(BaseContext):
    """Per-request GraphQL context: the wired use cases + a fresh loader.

    ``BaseContext`` is what strawberry's FastAPI integration accepts as a
    custom context (or a plain dict); carrying the posts bundle and ONE
    ``AuthorLoader`` here means the loader's batch and cache live exactly
    as long as the request that needed them.
    """

    def __init__(self, posts: PostUseCases, authors: AuthorLoader) -> None:
        super().__init__()
        self.posts = posts
        self.authors = authors


@strawberry.type
class Post:
    """One posts-substrate post, as the schema serves it (camelCase wire)."""

    id: str
    title: str
    body: str
    tags: list[str]
    status: PostStatus
    created_at: str = strawberry.field(name="createdAt")
    updated_at: str = strawberry.field(name="updatedAt")
    author_name: str = strawberry.field(
        name="authorName", description="The stored byline string — the loader's key."
    )

    @strawberry.field
    async def author(self, info: strawberry.Info[GraphQLContext, None]) -> Author | None:
        """The byline as a projected author — batched per request by the loader."""
        return await info.context.authors.load(self.author_name)

    @classmethod
    def from_domain(cls, post: DomainPost) -> "Post":
        """Project the domain snapshot onto the schema type (pure)."""
        return cls(
            id=post.id,
            title=post.title,
            body=post.body,
            tags=list(post.tags),
            status=PostStatus(post.status),
            created_at=post.created_at,
            updated_at=post.updated_at,
            author_name=post.author,
        )


@strawberry.type
class PostPage:
    """One filtered, sorted, paginated answer — totals like the REST page."""

    items: list[Post]
    total: int
    page: int
    limit: int
    pages: int

    @classmethod
    def from_domain(cls, page: DomainPage) -> "PostPage":
        """Project the domain page onto the schema type (pure)."""
        return cls(
            items=[Post.from_domain(post) for post in page.items],
            total=page.total,
            page=page.page,
            limit=page.limit,
            pages=page.pages,
        )


@strawberry.input
class PostFilter:
    """The collection's exact-match filters — GET /api/posts's query surface."""

    author: str | None = None
    tag: str | None = None
    status: PostStatus | None = None


@strawberry.input
class CreatePostInput:
    """The mutation input; the domain draft's bounds re-run at the edge."""

    title: str
    body: str = ""
    author: str
    tags: list[str] = strawberry.field(default_factory=list)
    status: PostStatus = PostStatus.DRAFT


def _validation_error(operation: str, exc: ValidationError) -> GraphQLError:
    """Map pydantic's edge validation onto the family's error vocabulary."""
    details = [
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    ]
    return GraphQLError(
        message=f"{operation} arguments failed validation.",
        extensions={"code": FailureKind.VALIDATION_FAILED.value, "details": details},
    )


@strawberry.type
class Query:
    """The read side: the collection as a typed page, and one post by slug."""

    @strawberry.field
    def posts(
        self,
        info: strawberry.Info[GraphQLContext, None],
        page: int = 1,
        limit: int = DEFAULT_LIST_LIMIT,
        sort: PostSort = PostSort.NEWEST,
        filter: PostFilter | None = None,
    ) -> PostPage:
        """One filtered, sorted, paginated page of posts (the page size caps at 100)."""
        chosen = filter if filter is not None else PostFilter()
        try:
            query = PostListQuery(
                page=page,
                limit=limit,
                sort=sort.value,
                author=chosen.author,
                tag=chosen.tag,
                status=chosen.status.value if chosen.status is not None else None,
            )
        except ValidationError as exc:
            raise _validation_error("posts", exc) from exc
        result = info.context.posts.list_posts.execute(query)
        if isinstance(result, Err):
            raise result.failure
        return PostPage.from_domain(result.value)

    @strawberry.field
    def post(self, info: strawberry.Info[GraphQLContext, None], slug: str) -> Post:
        """One post by its slug id; an unknown slug errors typed, not fatally."""
        result = info.context.posts.get_post.execute(slug)
        if isinstance(result, Err):
            failure = result.failure
            raise GraphQLError(
                message=failure.message,
                extensions={
                    "code": failure.kind.value,
                    "entity": "Post",
                    "slug": slug,
                },
            ) from failure
        return Post.from_domain(result.value)


@strawberry.type
class Mutation:
    """The write side: create, through the same use case POST /api/posts runs."""

    @strawberry.mutation
    def create_post(
        self, info: strawberry.Info[GraphQLContext, None], input: CreatePostInput
    ) -> Post:
        """Create from the input; the draft's bounds run as a GraphQL error."""
        try:
            draft = PostCreate(
                title=input.title,
                body=input.body,
                author=input.author,
                tags=input.tags,
                status=input.status.value,
            )
        except ValidationError as exc:
            raise _validation_error("createPost", exc) from exc
        result = info.context.posts.create_post.execute(draft)
        if isinstance(result, Err):
            raise result.failure
        return Post.from_domain(result.value)


schema = strawberry.Schema(query=Query, mutation=Mutation)


def build_graphql_context(request: Request) -> GraphQLContext:
    """FastAPI dependency: the SAME posts bundle the REST router resolves."""
    use_cases = get_post_use_cases(request)
    return GraphQLContext(posts=use_cases, authors=AuthorLoader(use_cases.list_posts))


router = GraphQLRouter(
    schema,
    path=GRAPHQL_PATH,
    context_getter=build_graphql_context,
    include_in_schema=False,
    tags=["graphql"],
)
"""The mounted GraphQL API: POST queries at /api/graphql, GraphiQL on GET."""
