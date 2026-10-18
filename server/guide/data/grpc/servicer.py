"""The PostService servicer: gRPC's half of a thin router, over posts.

``PostServiceServicer`` subclasses the generated base class
(``guide_pb2_grpc.PostServiceServicer``, compiled from ``guide.proto``)
and implements all four RPC shapes over the SAME ``PostUseCases`` bundle
the REST router (topic 11) and the GraphQL resolvers (topic 13) resolve
— one domain, three front doors. The discipline is the family's
thin-router invariant carried across protocols: parse nothing (the
decoder already produced typed fields), call the use case, map the
``Result`` to the protocol's answer — here ``context.abort`` with a
grpc status code instead of an HTTP envelope.

Two behaviors are deliberate teaching surfaces:

- ``StreamPosts`` pauses ``STREAM_PAUSE_SECONDS`` between messages — the
  "slow method" that makes deadlines VISIBLE: a caller with a short
  deadline receives the first few messages and then DEADLINE_EXCEEDED
  (section 6), which is the honest production shape of a stream that
  outlives its budget;
- an unknown slug aborts NOT_FOUND — real status propagation, the gRPC
  sibling of the REST 404 envelope and GraphQL's typed error.

Types are honest about the compiled layer: the generated base class is
excluded from mypy (build output), so ``request``/message types surface
as ``Any`` — the DOMAIN port (``guide.domain.grpc``) is the typed seam.
"""

import asyncio
from collections import Counter
from collections.abc import AsyncIterator
from typing import Any

import grpc

from guide.core.result import Err
from guide.domain.grpc.entities import STREAM_PAUSE_SECONDS
from guide.domain.posts.entities import Post, PostListQuery
from guide.domain.posts.use_cases import PostUseCases
from guide.grpcapi import guide_pb2, guide_pb2_grpc


def _reply_from_post(post: Post) -> Any:
    """Project a domain post onto the compiled ``PostReply`` message."""
    return guide_pb2.PostReply(
        slug=post.id,
        title=post.title,
        author=post.author,
        status=post.status,
        tags=list(post.tags),
        created_at=post.created_at,
    )


class PostServiceServicer(guide_pb2_grpc.PostServiceServicer):
    """The four RPC shapes over the posts use cases (inbound adapter)."""

    def __init__(self, posts: PostUseCases) -> None:
        self._posts = posts

    async def GetPost(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        """UNARY: one post by slug, or NOT_FOUND — the gRPC 404."""
        result = self._posts.get_post.execute(request.slug)
        if isinstance(result, Err):
            await context.abort(grpc.StatusCode.NOT_FOUND, result.failure.message)
        return _reply_from_post(result.value)

    async def StreamPosts(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[Any]:
        """SERVER-STREAMING: every matching post, one message each, paused.

        The pause (``STREAM_PAUSE_SECONDS``, domain-owned so the console's
        roster reports the same fact) is the deliberate slowness that makes
        deadlines visible: a short deadline lands mid-stream with a few
        messages already delivered — section 6's exact scenario.
        """
        result = self._posts.list_posts.execute(
            PostListQuery(limit=100, sort="oldest", tag=request.tag or None)
        )
        if isinstance(result, Err):  # pragma: no cover - in-memory list cannot fail
            await context.abort(grpc.StatusCode.INTERNAL, result.failure.message)
            return
        for post in result.value.items:
            await asyncio.sleep(STREAM_PAUSE_SECONDS)
            yield _reply_from_post(post)

    async def CountViews(
        self, request_iterator: AsyncIterator[Any], context: grpc.aio.ServicerContext
    ) -> Any:
        """CLIENT-STREAMING: consume view events, answer one summary."""
        events = 0
        per_post: Counter[str] = Counter()
        viewers: set[str] = set()
        async for event in request_iterator:
            events += 1
            per_post[event.slug] += 1
            viewers.add(event.viewer)
        return guide_pb2.ViewsSummary(
            events=events,
            unique_posts=len(per_post),
            unique_viewers=len(viewers),
            views_per_post=dict(per_post),
        )

    async def EchoChat(
        self, request_iterator: AsyncIterator[Any], context: grpc.aio.ServicerContext
    ) -> AsyncIterator[Any]:
        """BIDIRECTIONAL: echo each note back as it arrives."""
        async for note in request_iterator:
            yield note
