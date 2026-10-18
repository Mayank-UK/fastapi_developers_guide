"""The posts use cases: thin orchestration over the ``PostRepository`` port.

Each use case returns a ``Result`` so control flow stays explicit and the
router decides how a failure maps onto HTTP (the domain never throws across
layers — topic 32 takes that principle deeper). They are deliberately thin
because the models already carry every rule (topic 10): a draft or query
that exists is valid, so there is nothing left to re-check. What the use
cases own is the EXISTENCE question — a missing post is ``Err(not_found)``,
a domain answer, never a validation one — and the seam where later topics
(rich listing rules, authorization) will grow real logic.

``PostUseCases`` bundles the four into one frozen value the composition
root wires once; routers resolve the bundle through a single dependency.
"""

from dataclasses import dataclass
from typing import final

from guide.core.errors import AppError, FailureKind
from guide.core.result import Err, Ok, Result
from guide.domain.posts.entities import Post, PostCreate, PostListQuery, PostPage
from guide.domain.posts.ports import PostRepository


class ListPostsUseCase:
    """Serve one filtered, sorted, paginated page through the port."""

    def __init__(self, posts: PostRepository) -> None:
        self._posts = posts

    def execute(self, query: PostListQuery) -> Result[PostPage]:
        """Ask the port; the query's own constraints guarantee its shape."""
        return Ok(self._posts.list(query))


class GetPostUseCase:
    """Serve one post by id; existence is this layer's answer."""

    def __init__(self, posts: PostRepository) -> None:
        self._posts = posts

    def execute(self, post_id: str) -> Result[Post]:
        """Ok(post), or Err(not_found) carrying the client-safe message."""
        post = self._posts.get(post_id)
        if post is None:
            return Err(AppError(FailureKind.NOT_FOUND, f"Post {post_id!r} not found"))
        return Ok(post)


class CreatePostUseCase:
    """Create from a validated draft; the adapter mints identity."""

    def __init__(self, posts: PostRepository) -> None:
        self._posts = posts

    def execute(self, draft: PostCreate) -> Result[Post]:
        """Ok(the stored snapshot) — the draft's constraints already ran."""
        return Ok(self._posts.create(draft))


class ReplacePostUseCase:
    """Full-replace one post's content; identity metadata survives."""

    def __init__(self, posts: PostRepository) -> None:
        self._posts = posts

    def execute(self, post_id: str, draft: PostCreate) -> Result[Post]:
        """Ok(replaced), or Err(not_found) — replace never creates."""
        post = self._posts.replace(post_id, draft)
        if post is None:
            return Err(AppError(FailureKind.NOT_FOUND, f"Post {post_id!r} not found"))
        return Ok(post)


@final
@dataclass(frozen=True, slots=True)
class PostUseCases:
    """The four posts use cases, wired once per app in the composition root."""

    list_posts: ListPostsUseCase
    get_post: GetPostUseCase
    create_post: CreatePostUseCase
    replace_post: ReplacePostUseCase
