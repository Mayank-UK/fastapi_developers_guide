"""The role→permission registry: four roles over four actions, pure data.

RBAC's entire world lives in one table: ROLES (viewer, author, editor,
admin) GRANT ACTIONS (posts:read, posts:write, comments:read,
comments:moderate) at a REACH — ``any`` object of the kind, or only the
principal's ``own``. The registry is deliberately in-domain and pure
(no store, no database): it is configuration the way constants are
configuration, and the policy engine reads it the way code reads a
lookup table. Actions are dotted ``<area>:<verb>`` strings — the same
vocabulary topic 23's scopes speak, which is what makes scope narrowing
a set intersection instead of a translation problem.

``ROLE_ASSIGNMENTS`` maps the demo usernames to their roles — the posts
substrate's authors (grace, alan, barbara) plus ada, so ownership
teaching has real owners and role bypass has real bystanders.
"""

from dataclasses import dataclass
from typing import Final, Literal

from guide.domain.authz.model import GrantLevel

Action = Literal["posts:read", "posts:write", "comments:read", "comments:moderate"]
"""The closed action vocabulary — everything else is denied by default."""

ACTIONS: Final[tuple[Action, ...]] = (
    "posts:read",
    "posts:write",
    "comments:read",
    "comments:moderate",
)
"""Every action the registry knows; the engine denies all others."""

WILDCARD_SCOPE: Final = "*"
"""The full-authority scope: a user token minted with it skips narrowing.

For a USER principal the wildcard means "all my roles' grants" — the
mint form's way to hand a principal its complete authority. For a
PROGRAM principal (an API key) it unlocks nothing: keys have no roles
behind them, and the engine fails closed on the confusion rather than
granting everything.
"""


@dataclass(frozen=True, slots=True)
class Grant:
    """One registry cell: role X grants action A at reach ``level``.

    Carries its ``role`` so a Decision's reason can name the authority
    that allowed the action — the teaching surface rides the grant.
    """

    action: Action
    level: GrantLevel
    role: str


GrantSpec = tuple[Action, GrantLevel]
"""One registry cell before the role is attached: action + reach."""

_GRANT_TABLE: Final[dict[str, tuple[GrantSpec, ...]]] = {
    "viewer": (
        ("posts:read", "any"),
        ("comments:read", "any"),
    ),
    "author": (
        ("posts:read", "any"),
        ("posts:write", "own"),
        ("comments:read", "any"),
    ),
    "editor": (
        ("posts:read", "any"),
        ("posts:write", "any"),
        ("comments:read", "any"),
    ),
    "admin": (
        ("posts:read", "any"),
        ("posts:write", "any"),
        ("comments:read", "any"),
        ("comments:moderate", "any"),
    ),
}
"""The matrix itself: role → (action, reach) cells. Own-reach is the
author's edge — edit YOUR posts; any-reach is the role bypass — edit
EVERYONE's. Admin alone moderates comments."""

ROLE_ORDER: Final[tuple[str, ...]] = ("viewer", "author", "editor", "admin")
"""Display order — least to most authority, the panel's row order."""

ROLE_CATALOG: Final[dict[str, tuple[Grant, ...]]] = {
    role: tuple(Grant(action=action, level=level, role=role) for action, level in specs)
    for role, specs in _GRANT_TABLE.items()
}
"""The compiled registry: role → grants, each grant naming its role."""

ROLE_ASSIGNMENTS: Final[dict[str, str]] = {
    "ada": "admin",
    "grace": "author",
    "alan": "viewer",
    "barbara": "editor",
}
"""Who has which role — the four principals the matrix demo walks with.

grace/alan/barbara are the posts substrate's authors (ownership has real
owners); ada owns nothing, so her admin reach is visibly a ROLE bypass,
not ownership in disguise. Unknown usernames simply have no entry — and
no entry means no roles, which means deny: the assignment map fails
closed without trying.
"""
