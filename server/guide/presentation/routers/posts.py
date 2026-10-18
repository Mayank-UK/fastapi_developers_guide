"""The real posts resource: ``/api/posts``, thin router over the use cases.

This is production-shaped code, not a demo exhibit: parse/validate input →
call a use case → map ``Result`` to an HTTP response (family invariant),
with the posts port wired by the composition root — this module imports
the DOMAIN only; which adapter answers is ``create_app``'s decision.

The resource surface: ``GET /api/posts`` serves one filtered, sorted,
paginated page with pagination facts in headers (``x-total-count``,
``x-page-count``, RFC 8288 ``Link`` for prev/next — links share the
canonical builder with the workbench demo, so the two cannot drift);
``GET /api/posts/{post_id}`` serves one post or the shared 404 envelope;
``POST /api/posts`` validates a ``PostCreate`` body and answers 201 +
Location (resolved with ``url_path_for``, never string-pasted); ``PUT``
full-replaces and answers 200. No DELETE — an honest design choice this
topic teaches, so DELETE earns the framework's 405 through the shared
envelope. A failed ``Result`` is raised as its ``AppError`` so the ONE
exception-handler pipeline renders the family envelope.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from guide.core.errors import AppError, FailureKind
from guide.core.result import Err
from guide.domain.posts.entities import Post, PostCreate, PostListQuery, PostPage
from guide.domain.posts.pagination import build_page_links, format_link_header
from guide.domain.posts.use_cases import PostUseCases

router = APIRouter(tags=["posts"])


def get_post_use_cases(request: Request) -> PostUseCases:
    """FastAPI dependency: the posts use cases (wired in create_app)."""
    bundle = request.app.state.posts_use_cases
    if not isinstance(bundle, PostUseCases):
        raise AppError(FailureKind.INTERNAL, "Post use cases not wired on app.state")
    return bundle


PostUseCasesDep = Annotated[PostUseCases, Depends(get_post_use_cases)]


@router.get("/api/posts", response_model=PostPage)
def list_posts(
    query: Annotated[PostListQuery, Depends()],
    use_cases: PostUseCasesDep,
    response: Response,
) -> PostPage:
    """Serve one filtered, sorted, paginated page; pagination in headers."""
    result = use_cases.list_posts.execute(query)
    if isinstance(result, Err):
        raise result.failure
    page = result.value
    response.headers["x-total-count"] = str(page.total)
    response.headers["x-page-count"] = str(page.pages)
    link_header = format_link_header(build_page_links(query, page.total))
    if link_header is not None:
        response.headers["link"] = link_header
    return page


@router.get("/api/posts/{post_id}", response_model=Post)
def read_post(post_id: str, use_cases: PostUseCasesDep) -> Post:
    """Serve one post; unknown ids are the shared 404 envelope."""
    result = use_cases.get_post.execute(post_id)
    if isinstance(result, Err):
        raise result.failure
    return result.value


@router.post("/api/posts", response_model=Post, status_code=201)
def create_post(draft: PostCreate, response: Response, use_cases: PostUseCasesDep) -> Post:
    """Create from the validated body: 201 + Location names the resource."""
    result = use_cases.create_post.execute(draft)
    if isinstance(result, Err):
        raise result.failure
    post = result.value
    response.headers["location"] = router.url_path_for("read_post", post_id=post.id)
    return post


@router.put("/api/posts/{post_id}", response_model=Post)
def replace_post(post_id: str, draft: PostCreate, use_cases: PostUseCasesDep) -> Post:
    """Full-replace the post's content: 200 with the new representation."""
    result = use_cases.replace_post.execute(post_id, draft)
    if isinstance(result, Err):
        raise result.failure
    return result.value
