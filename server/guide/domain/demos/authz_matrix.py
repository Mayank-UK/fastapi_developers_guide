"""The authz matrix demo payload: the registry, derived purely.

``GET /api/demo/authz`` serves the panel (topic 24's demo
``authz:matrix``, inline in the RBAC section): the seeded principals
with their roles, the roles→grants matrix as rows, the seeded posts and
comments that give ownership real objects, and the notes that pin the
engine's semantics. ``run_matrix_check`` is the interactive half — a
pure function that takes an already-built principal, action, and
optional resource and returns the decision as a wire row (the ROUTER
does the lookups; this module only shapes).
"""

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import Field

from guide.core.serialization import CamelModel
from guide.domain.authz.comments import DemoComment
from guide.domain.authz.engine import PolicyEngine
from guide.domain.authz.model import Decision, OwnedResource, Principal
from guide.domain.authz.roles import (
    ROLE_ASSIGNMENTS,
    ROLE_CATALOG,
    ROLE_ORDER,
    WILDCARD_SCOPE,
    Action,
)
from guide.domain.posts.entities import Post

DENY_BY_DEFAULT_NOTE = (
    "the engine answers deny for everything it does not know: unknown actions, "
    "principals without a role, objects that do not exist — fail closed is the "
    "default, allowance is the exception someone granted"
)
"""The default-deny contract, stated where the suite can pin it."""

SCOPE_NOTE = (
    "credential scopes narrow role grants (an intersection — they can remove "
    f"authority, never add it); the {WILDCARD_SCOPE} scope is full authority for a "
    "user's roles and unlocks nothing for an API key, which has no roles behind it"
)
"""The scope semantics, stated where the suite can pin it."""

OWNERSHIP_NOTE = (
    "own-reach grants answer 'can edit THIS one' — the owner check is the "
    "authority; any-reach grants are the role bypass — editors and admins act on "
    "everyone's objects, ada most visibly because she owns none"
)
"""The ownership rules, stated where the suite can pin it."""


class PrincipalRow(CamelModel):
    """One seeded principal: name, role, and the credential note that teaches."""

    name: str
    display_name: str
    role: str | None
    kind: Literal["user", "program"]
    note: str


class GrantRow(CamelModel):
    """One matrix cell: the action and the reach granted (None = not granted)."""

    action: str
    level: Literal["any", "own"] | None


class RoleRow(CamelModel):
    """One matrix row: the role and its grant cells, in action order."""

    role: str
    grants: list[GrantRow]


class SeededPostRow(CamelModel):
    """One ownership target: a seeded post and its owner."""

    id: str
    title: str
    author: str


class SeededCommentRow(CamelModel):
    """One moderation target: a seeded comment, its owner, its status."""

    id: str
    post_id: str
    author: str
    status: str


class AuthzPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/authz`` — the matrix panel's contract."""

    principals: list[PrincipalRow]
    roles: list[RoleRow]
    seeded_posts: list[SeededPostRow]
    seeded_comments: list[SeededCommentRow]
    wildcard_scope: str
    deny_note: str
    scope_note: str
    ownership_note: str
    check_endpoint: str
    edit_post_endpoint: str
    moderate_comment_endpoint: str
    reasoning: str


_PRINCIPAL_NOTES: Mapping[str, str] = {
    "ada": (
        "admin — owns no posts, so every allow she gets is visibly the role "
        "bypass; her login token carries only [posts:read, posts:write], so "
        f"moderation needs a minted {WILDCARD_SCOPE} token (scope narrowing bites)"
    ),
    "grace": (
        "author — owns four seeded posts; can edit HER posts, nobody else's. "
        "Her login token carries only [posts:read], so the write paths need a "
        f"minted {WILDCARD_SCOPE} token to show the role's full reach"
    ),
    "alan": (
        "viewer — owns three seeded posts and still cannot edit them: "
        "ownership attaches to actions, and 'viewer' carries no write grant"
    ),
    "barbara": (
        "editor — owns three posts but does not need them: any-reach lets her "
        "edit ANYONE's post; moderation is the one action she lacks"
    ),
}
"""The per-principal teaching notes — the panel's punchlines."""


def build_authz_panel_payload(
    *,
    display_names: Mapping[str, str],
    seeded_posts: Sequence[Post],
    seeded_comments: Sequence[DemoComment],
    check_endpoint: str,
    edit_post_endpoint: str,
    moderate_comment_endpoint: str,
) -> AuthzPanelPayload:
    """Shape the panel (pure): roster, matrix, targets, notes."""
    principals = [
        PrincipalRow(
            name=name,
            display_name=display_names.get(name, name),
            role=ROLE_ASSIGNMENTS.get(name),
            kind="user",
            note=_PRINCIPAL_NOTES.get(name, "no role assignment — deny by default"),
        )
        for name in sorted(ROLE_ASSIGNMENTS)
    ]
    roles = [
        RoleRow(
            role=role,
            grants=[
                GrantRow(action=action, level=level)
                for action, level in _grant_levels(role)
            ],
        )
        for role in ROLE_ORDER
    ]
    return AuthzPanelPayload(
        principals=principals,
        roles=roles,
        seeded_posts=[
            SeededPostRow(id=post.id, title=post.title, author=post.author)
            for post in seeded_posts
        ],
        seeded_comments=[
            SeededCommentRow(
                id=comment.id, post_id=comment.post_id, author=comment.author,
                status=comment.status,
            )
            for comment in seeded_comments
        ],
        wildcard_scope=WILDCARD_SCOPE,
        deny_note=DENY_BY_DEFAULT_NOTE,
        scope_note=SCOPE_NOTE,
        ownership_note=OWNERSHIP_NOTE,
        check_endpoint=check_endpoint,
        edit_post_endpoint=edit_post_endpoint,
        moderate_comment_endpoint=moderate_comment_endpoint,
        reasoning=(
            "Four roles over four actions, two reaches (any = the role bypass, "
            "own = the owner check), and credential scopes narrowing it all from "
            "the side: that is the whole model. The check below runs the REAL "
            "engine over it; the guarded endpoints then prove the same verdicts "
            "hold on the wire — 401 before you are anyone, 403 with a reason "
            "once you are someone the engine says no to."
        ),
    )


def _grant_levels(role: str) -> list[tuple[Action, str | None]]:
    """One role's matrix cells across every action, in action order."""
    granted = {grant.action: grant.level for grant in ROLE_CATALOG[role]}
    return [(action, granted.get(action)) for action in _ACTION_ORDER]


_ACTION_ORDER: tuple[Action, ...] = (
    "posts:read",
    "posts:write",
    "comments:read",
    "comments:moderate",
)
"""The matrix's column order — read, write, then the comment pair."""


def simulated_principal(name: str, scopes: Sequence[str] | None) -> Principal:
    """Build the check's principal: roles from the registry, scopes as given.

    ``scopes`` None means full authority (the wildcard) — the panel's
    what-if default; an explicit list is the narrowing the caller wants
    to explore.
    """
    role = ROLE_ASSIGNMENTS.get(name)
    return Principal(
        kind="user",
        name=name,
        display_name=name,
        roles=(role,) if role is not None else (),
        scopes=tuple(scopes) if scopes is not None else (WILDCARD_SCOPE,),
        via="the matrix panel's what-if check — no credential was presented",
    )


class DecisionRow(CamelModel):
    """The verdict as wire: allowed, and the reason the engine gave."""

    allowed: bool
    reason: str


class ResourceRow(CamelModel):
    """The object a verdict was computed over, when there was one."""

    kind: str
    id: str
    owner: str


class AuthzCheckRow(CamelModel):
    """Wire shape of ``POST /api/demo/authz/check`` — one what-if verdict."""

    principal: str
    role: str | None
    scopes: list[str]
    action: str
    resource: ResourceRow | None
    decision: DecisionRow
    detail: str


def build_check_row(
    *,
    principal: Principal,
    action: str,
    resource: OwnedResource | None,
    resource_found: bool,
    engine: PolicyEngine,
) -> AuthzCheckRow:
    """Run the engine and shape the verdict (pure) — including the deny paths."""
    if resource is not None and not resource_found:
        decision = Decision(
            allowed=False,
            reason=(
                f"no such {resource.kind} {resource.id!r} — there is nothing to "
                "authorize, and the engine does not invent objects"
            ),
        )
    else:
        decision = engine.decide(principal, action, resource)
    role = principal.roles[0] if principal.roles else None
    return AuthzCheckRow(
        principal=principal.name,
        role=role,
        scopes=list(principal.scopes),
        action=action,
        resource=(
            ResourceRow(kind=resource.kind, id=resource.id, owner=resource.owner)
            if resource is not None
            else None
        ),
        decision=DecisionRow(allowed=decision.allowed, reason=decision.reason),
        detail=(
            f"{principal.name!r} ({role or 'no role'}, scopes "
            f"{list(principal.scopes)}) asks for {action!r}"
            + (
                f" on {resource.kind} {resource.id!r} owned by {resource.owner!r}"
                if resource is not None
                else ""
            )
            + f" — the engine says {'ALLOW' if decision.allowed else 'DENY'}"
        ),
    )


class GuardedOutcomeRow(CamelModel):
    """What a guarded endpoint answers on success: who, what, and why allowed."""

    principal: str
    principal_kind: Literal["user", "program"]
    action: str
    resource_kind: str
    resource_id: str
    reason: str
    via: str
    detail: str


class EditedPostRow(GuardedOutcomeRow):
    """The edit endpoint's success row — plus the post as it now stands."""

    post: Post


class ModeratedCommentRow(GuardedOutcomeRow):
    """The moderate endpoint's success row — plus the comment's new status."""

    comment: DemoComment


# ── Request bodies (routers parse; bounds are the contract) ──────────────────


class AuthzCheckRequest(CamelModel):
    """The check form's body: who asks, for what, on which object.

    ``action`` is a free string on purpose — unknown actions are the
    deny-by-default lesson. ``scopes`` None means full authority (the
    wildcard); an explicit list explores narrowing. ``resource`` is
    optional: read actions need no object, write actions do.
    """

    principal_name: str = Field(min_length=1, max_length=60)
    action: str = Field(min_length=1, max_length=64)
    scopes: list[str] | None = Field(default=None, max_length=8)
    resource_kind: Literal["post", "comment"] | None = None
    resource_id: str | None = Field(default=None, min_length=1, max_length=120)


class EditPostRequest(CamelModel):
    """The edit form's body: title and body, either may be omitted to keep.

    An empty edit (both omitted) is a legitimate no-op replace — the
    real PUT round the demo runs without touching content.
    """

    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=5000)


class ModerateCommentRequest(CamelModel):
    """The moderation form's body: the comment's next status."""

    status: Literal["visible", "hidden"]
