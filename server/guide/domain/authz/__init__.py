"""The authorization domain area: the verdict layer over topic 23's identity.

``model.py`` is the vocabulary (principals, owned resources, decisions);
``roles.py`` is the role→permission registry plus the demo assignments;
``engine.py`` is the pure policy engine — one ``decide()`` walking
deny-by-default, scope narrowing, and ownership in order;
``principals.py`` resolves verified credentials into principals (roles
from the registry, scopes from the credential); ``comments.py`` is the
small seeded ledger that gives the admin-only moderation action a real
object to act on. Everything here is driver-free and synchronous-pure
where possible — the engine consults nothing but its arguments.
"""

from guide.domain.authz.comments import CommentLedger, DemoComment
from guide.domain.authz.engine import PolicyEngine
from guide.domain.authz.model import Decision, OwnedResource, Principal
from guide.domain.authz.principals import PrincipalResolver
from guide.domain.authz.roles import (
    ACTIONS,
    ROLE_ASSIGNMENTS,
    ROLE_CATALOG,
    ROLE_ORDER,
    WILDCARD_SCOPE,
    Action,
    Grant,
)

__all__ = [
    "ACTIONS",
    "Action",
    "CommentLedger",
    "Decision",
    "DemoComment",
    "Grant",
    "OwnedResource",
    "PolicyEngine",
    "Principal",
    "PrincipalResolver",
    "ROLE_ASSIGNMENTS",
    "ROLE_CATALOG",
    "ROLE_ORDER",
    "WILDCARD_SCOPE",
]
