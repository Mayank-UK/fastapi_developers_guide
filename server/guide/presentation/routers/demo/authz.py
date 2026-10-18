"""The authorization demos: topic 24's matrix lab (area ``authz``).

Thin routers (family invariant) — and the thinness is the LESSON here:
the two guarded endpoints contain no authority logic at all, because
``Depends(require_owner_or(...))`` / ``Depends(require_permission(...))``
IS the guard. ``GET /api/demo/authz`` serves the panel payload (roster,
matrix, targets, notes); ``POST /check`` runs the engine as a what-if
over the seeded world (deny-shaped answers included — it is a panel,
not an enforcement point); ``PUT /posts/{post_id}`` is the real
object-level guard over the posts substrate (401 → 404 → 403-with-reason
→ 200); ``POST /comments/{comment_id}/moderate`` is the real
collection-level guard over the comment ledger (401 → 403 → 404 → 200 —
the verdict precedes existence here, because the guard needs no object).
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request

from guide.core.errors import AppError, FailureKind
from guide.core.result import Err
from guide.domain.auth.ports import UserDirectory
from guide.domain.authz.comments import CommentLedger
from guide.domain.authz.model import OwnedResource
from guide.domain.authz.roles import Action
from guide.domain.demos.authz_matrix import (
    AuthzCheckRequest,
    AuthzCheckRow,
    AuthzPanelPayload,
    EditedPostRow,
    EditPostRequest,
    ModerateCommentRequest,
    ModeratedCommentRow,
    build_authz_panel_payload,
    build_check_row,
    simulated_principal,
)
from guide.domain.posts.entities import PostCreate, PostListQuery
from guide.presentation.dependencies.authz import (
    EngineDep,
    Guarded,
    GuardedPost,
    PostsDep,
    require_owner_or,
    require_permission,
)

router = APIRouter(prefix="/api/demo/authz", tags=["demo:authz"])

PANEL_PATH: Final = ""
CHECK_PATH: Final = "/check"
EDIT_POST_PATH: Final = "/posts/{post_id}"
MODERATE_COMMENT_PATH: Final = "/comments/{comment_id}/moderate"
"""The lab's paths — the terminal companion's tour names them."""

EDIT_ACTION: Final[Action] = "posts:write"
MODERATE_ACTION: Final[Action] = "comments:moderate"
"""The two actions the guarded endpoints enforce."""

PANEL_POST_LIMIT: Final = 12
"""How many posts the panel lists: the deterministic seed, oldest first —
created posts sort after it under ``oldest``, so the panel stays stable
even as the live stack accumulates them."""


def get_comment_ledger(request: Request) -> CommentLedger:
    """FastAPI dependency: the seeded comment ledger (wired in create_app)."""
    ledger = request.app.state.authz_comments
    if not isinstance(ledger, CommentLedger):
        raise AppError(FailureKind.INTERNAL, "Comment ledger not wired on app.state")
    return ledger


def get_user_directory(request: Request) -> UserDirectory:
    """FastAPI dependency: the seeded directory, for display names."""
    directory = request.app.state.auth_state
    if not isinstance(directory, UserDirectory):
        raise AppError(FailureKind.INTERNAL, "User directory not wired on app.state")
    return directory


LedgerDep = Annotated[CommentLedger, Depends(get_comment_ledger)]
DirectoryDep = Annotated[UserDirectory, Depends(get_user_directory)]

EditGuard = Annotated[GuardedPost, Depends(require_owner_or(EDIT_ACTION))]
ModerateGuard = Annotated[Guarded, Depends(require_permission(MODERATE_ACTION))]


@router.get(PANEL_PATH, response_model=AuthzPanelPayload)
async def read_authz_panel(
    directory: DirectoryDep, posts: PostsDep, ledger: LedgerDep
) -> AuthzPanelPayload:
    """The matrix panel: roster, roles→grants, targets, and the pinned notes."""
    users = await directory.list_users()
    display_names = {user.username: user.display_name for user in users}
    seed_page = posts.list_posts.execute(
        PostListQuery(limit=PANEL_POST_LIMIT, sort="oldest")
    ).value
    return build_authz_panel_payload(
        display_names=display_names,
        seeded_posts=seed_page.items,
        seeded_comments=ledger.list(),
        check_endpoint=f"{router.prefix}{CHECK_PATH}",
        edit_post_endpoint=f"{router.prefix}/posts/{{post_id}}",
        moderate_comment_endpoint=f"{router.prefix}/comments/{{comment_id}}/moderate",
    )


@router.post(CHECK_PATH, response_model=AuthzCheckRow)
async def run_check(
    request: AuthzCheckRequest, posts: PostsDep, ledger: LedgerDep, engine: EngineDep
) -> AuthzCheckRow:
    """The what-if check: build the principal, find the object, decide."""
    resource: OwnedResource | None = None
    resource_found = False
    if request.resource_kind is not None and request.resource_id is not None:
        # A missing object still gets a placeholder row, so the check can
        # answer the fail-closed "nothing to authorize" deny instead of
        # silently deciding an object-less question.
        if request.resource_kind == "post":
            post_result = posts.get_post.execute(request.resource_id)
            owner = post_result.value.author if not isinstance(post_result, Err) else ""
            resource = OwnedResource(kind="post", id=request.resource_id, owner=owner)
            resource_found = not isinstance(post_result, Err)
        else:
            comment = ledger.find(request.resource_id)
            owner = comment.author if comment is not None else ""
            resource = OwnedResource(kind="comment", id=request.resource_id, owner=owner)
            resource_found = comment is not None
    principal = simulated_principal(request.principal_name, request.scopes)
    return build_check_row(
        principal=principal,
        action=request.action,
        resource=resource,
        resource_found=resource_found,
        engine=engine,
    )


@router.put(EDIT_POST_PATH, response_model=EditedPostRow)
async def edit_post(
    guard: EditGuard,
    posts: PostsDep,
    request: EditPostRequest | None = None,
) -> EditedPostRow:
    """The object-level guard, live: owner-or-authority → real replace.

    The body itself may be absent — the no-op edit (keep title and body
    as they stand) is the demo's honest round trip.
    """
    edit = request if request is not None else EditPostRequest()
    current = guard.post
    draft = PostCreate(
        title=edit.title if edit.title is not None else current.title,
        body=edit.body if edit.body is not None else current.body,
        author=current.author,
        tags=current.tags,
        status=current.status,
    )
    result = posts.replace_post.execute(current.id, draft)
    if isinstance(result, Err):
        raise result.failure
    return EditedPostRow(
        principal=guard.principal.name,
        principal_kind=guard.principal.kind,
        action=EDIT_ACTION,
        resource_kind="post",
        resource_id=result.value.id,
        reason=guard.decision.reason,
        via=guard.principal.via,
        detail=(
            f"{guard.principal.name!r} replaced post {result.value.id!r} — the "
            "guard ran before the handler, and the handler never checked a thing"
        ),
        post=result.value,
    )


@router.post(MODERATE_COMMENT_PATH, response_model=ModeratedCommentRow)
async def moderate_comment(
    comment_id: str, guard: ModerateGuard, request: ModerateCommentRequest, ledger: LedgerDep
) -> ModeratedCommentRow:
    """The collection-level guard, live: the admin-only action over the ledger."""
    comment = ledger.moderate(comment_id, request.status, moderator=guard.principal.name)
    if comment is None:
        raise AppError(FailureKind.NOT_FOUND, f"Comment {comment_id!r} not found")
    return ModeratedCommentRow(
        principal=guard.principal.name,
        principal_kind=guard.principal.kind,
        action=MODERATE_ACTION,
        resource_kind="comment",
        resource_id=comment.id,
        reason=guard.decision.reason,
        via=guard.principal.via,
        detail=(
            f"{guard.principal.name!r} set comment {comment.id!r} to "
            f"{comment.status!r} — only the admin role carries this action"
        ),
        comment=comment,
    )
