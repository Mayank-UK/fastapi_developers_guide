"""The policy engine: one pure ``decide()`` answering every verdict.

``PolicyEngine.decide(principal, action, resource)`` is the ENTIRE
authorization surface — a pure function over the role registry with no
clock, no store, no I/O, so every matrix cell is testable as arithmetic.
The evaluation order is the topic's spine, and each rung produces its
own REASON (the teaching surface the demo and the 403 envelope show):

1. Unknown action → deny. The registry is a closed vocabulary; anything
   else fails closed before a single grant is read.
2. Program principals (API keys) → their scopes ARE their grants. A
   wildcard scope unlocks nothing for them (no roles behind it) and is
   denied outright — a confused credential gets the fail-closed answer.
3. User principals → union the grants of their roles, then NARROW by
   the credential's scopes: the intersection of what the roles grant
   and what the token carries. A wildcard scope skips the narrowing; an
   empty scope list intersects to nothing. Narrowing can only REMOVE
   authority — never add it.
4. The surviving grant's REACH decides the object question: ``any``
   allows on any object (the role bypass); ``own`` demands the resource
   AND the ownership match, with denials that say whose object it is.
"""

from guide.domain.authz.model import Decision, OwnedResource, Principal
from guide.domain.authz.roles import ACTIONS, ROLE_CATALOG, WILDCARD_SCOPE, Grant


def _scope_list(scopes: tuple[str, ...]) -> str:
    """Render a scope tuple for reasons — bracketed, readable, honest."""
    return "[" + ", ".join(scopes) + "]" if scopes else "[]"


class PolicyEngine:
    """The verdict machine — pure, stateless, one public method."""

    def decide(
        self, principal: Principal, action: str, resource: OwnedResource | None = None
    ) -> Decision:
        """Answer: may ``principal`` do ``action`` — on ``resource``, if any?"""
        if action not in ACTIONS:
            return Decision(
                allowed=False,
                reason=(
                    f"unknown action {action!r} — it is not in the registry, "
                    "and the engine denies what it does not know"
                ),
            )

        if principal.kind == "program":
            return self._decide_program(principal, action)

        grants = self._role_grants(principal)
        if not grants:
            return Decision(
                allowed=False,
                reason=(
                    f"{principal.name!r} has no role in the registry — "
                    "deny by default"
                ),
            )
        if WILDCARD_SCOPE not in principal.scopes:
            held = grants.get(action)
            if held is not None and action not in principal.scopes:
                return Decision(
                    allowed=False,
                    reason=(
                        f"role {held.role!r} grants {action} but the credential's "
                        f"scopes {_scope_list(principal.scopes)} do not include it "
                        "— scopes narrow, never widen"
                    ),
                )
            grants = {
                granted: grant for granted, grant in grants.items() if granted in principal.scopes
            }

        grant = grants.get(action)
        if grant is None:
            roles = ", ".join(repr(role) for role in principal.roles)
            return Decision(
                allowed=False,
                reason=f"no role of ({roles}) grants {action}",
            )
        return self._decide_reach(principal, action, grant, resource)

    def _decide_program(self, principal: Principal, action: str) -> Decision:
        """A program principal's authority is exactly its scopes — no roles."""
        if WILDCARD_SCOPE in principal.scopes:
            return Decision(
                allowed=False,
                reason=(
                    "a wildcard scope unlocks a principal's roles, and a program "
                    "credential has none — the engine fails closed on it"
                ),
            )
        if action in principal.scopes:
            return Decision(
                allowed=True,
                reason=(
                    f"the credential's scopes carry {action} directly — a program "
                    "principal's authority is exactly its scopes"
                ),
            )
        return Decision(
            allowed=False,
            reason=(
                f"the credential's scopes {_scope_list(principal.scopes)} do not "
                f"carry {action} — a program principal has no roles to fall back on"
            ),
        )

    @staticmethod
    def _role_grants(principal: Principal) -> dict[str, Grant]:
        """Union the grants of every known role — unknown roles contribute nothing."""
        grants: dict[str, Grant] = {}
        for role in principal.roles:
            for grant in ROLE_CATALOG.get(role, ()):
                grants.setdefault(grant.action, grant)
        return grants

    @staticmethod
    def _decide_reach(
        principal: Principal, action: str, grant: Grant, resource: OwnedResource | None
    ) -> Decision:
        """The object question: any-reach allows outright, own-reach checks ownership."""
        if grant.level == "any":
            target = resource.kind if resource is not None else "object"
            return Decision(
                allowed=True,
                reason=(
                    f"role {grant.role!r} grants {action} on any {target} — "
                    "the role is the authority"
                ),
            )
        if resource is None:
            return Decision(
                allowed=False,
                reason=(
                    f"{action} is own-scoped for role {grant.role!r} — it needs a "
                    "specific object, and none was given"
                ),
            )
        if resource.owner != principal.name:
            return Decision(
                allowed=False,
                reason=(
                    f"{action} is own-scoped, and this {resource.kind} "
                    f"{resource.id!r} belongs to {resource.owner!r}, not "
                    f"{principal.name!r}"
                ),
            )
        return Decision(
            allowed=True,
            reason=(
                f"{action} is own-scoped for role {grant.role!r} and "
                f"{principal.name!r} owns this {resource.kind} — ownership is "
                "the authority here"
            ),
        )
