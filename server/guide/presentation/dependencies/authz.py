"""Dependency-based enforcement: the authz guards handlers declare, not run.

This module is topic 24's thesis as code: authorization in FastAPI is a
DEPENDENCY you declare, not a branch you write. ``resolve_principal``
authenticates via topic 23's engines (Bearer token first, x-api-key
second, the standard 401 envelope when neither half holds) and resolves
the caller into a ``Principal``. ``require_permission(action)`` and
``require_owner_or(action)`` are FACTORIES: each call returns a FastAPI
dependency that resolves the principal, asks the pure policy engine for
a ``Decision``, and raises the standard 403 envelope (reason in
``details``) when the verdict is deny — so a guarded handler's body
never contains an ``if`` about authority at all.

The two factories answer the two halves of object-level authz.
``require_permission`` guards collection-level actions (moderate
comments) — the engine sees no object, and an own-scoped grant there
denies honestly ("needs a specific object"). ``require_owner_or``
guards object-level actions (edit THIS post): it fetches the resource
first — a missing post is the shared 404 the unguarded read would
answer — then decides WITH the object, so ownership and role bypass are
both real. Either way the handler receives a ``Guarded`` value carrying
the principal, the decision (reason included), and, for the object
guard, the resource the verdict was computed over.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any, Final

from fastapi import Depends, Header, Request

from guide.core.errors import AppError, FailureKind
from guide.core.result import Err
from guide.domain.auth.api_key_service import ApiKeyService
from guide.domain.auth.jwt_service import TokenService
from guide.domain.authz.engine import PolicyEngine
from guide.domain.authz.model import Decision, OwnedResource, Principal
from guide.domain.authz.principals import PrincipalResolver
from guide.domain.authz.roles import Action
from guide.domain.posts.entities import Post
from guide.domain.posts.use_cases import PostUseCases

BEARER_PREFIX: Final = "bearer "
"""Case-insensitive prefix the Authorization scheme check accepts."""

NOT_AUTHENTICATED_MESSAGE: Final = (
    "not authenticated — present a Bearer token (mint one at POST "
    "/api/demo/auth/jwt/mint) or an x-api-key header (generate one at POST "
    "/api/demo/auth/keys)"
)
"""The 401 the guards raise for a credential-less caller — with the doors named."""


@dataclass(frozen=True, slots=True)
class Guarded:
    """What a guard hands the handler: the principal plus the verdict it enforced."""

    principal: Principal
    decision: Decision


@dataclass(frozen=True, slots=True)
class GuardedPost(Guarded):
    """The object guard's answer: verdict plus the post it was computed over."""

    post: Post


def _token_service(request: Request) -> TokenService:
    """The token engine the Bearer half authenticates with (create_app wires)."""
    service = request.app.state.auth_tokens
    if not isinstance(service, TokenService):
        raise AppError(FailureKind.INTERNAL, "Token service not wired on app.state")
    return service


def _api_key_service(request: Request) -> ApiKeyService:
    """The key engine the x-api-key half authenticates with (create_app wires)."""
    service = request.app.state.auth_api_keys
    if not isinstance(service, ApiKeyService):
        raise AppError(FailureKind.INTERNAL, "API key service not wired on app.state")
    return service


def get_policy_engine(request: Request) -> PolicyEngine:
    """FastAPI dependency: the pure verdict engine (wired in create_app)."""
    engine = request.app.state.authz_engine
    if not isinstance(engine, PolicyEngine):
        raise AppError(FailureKind.INTERNAL, "Policy engine not wired on app.state")
    return engine


def get_principal_resolver(request: Request) -> PrincipalResolver:
    """FastAPI dependency: the credential→principal seam (wired in create_app)."""
    resolver = request.app.state.authz_resolver
    if not isinstance(resolver, PrincipalResolver):
        raise AppError(FailureKind.INTERNAL, "Principal resolver not wired on app.state")
    return resolver


def get_posts_use_cases(request: Request) -> PostUseCases:
    """FastAPI dependency: the posts bundle the object guard reads (create_app wires)."""
    bundle = request.app.state.posts_use_cases
    if not isinstance(bundle, PostUseCases):
        raise AppError(FailureKind.INTERNAL, "Post use cases not wired on app.state")
    return bundle


EngineDep = Annotated[PolicyEngine, Depends(get_policy_engine)]
PostsDep = Annotated[PostUseCases, Depends(get_posts_use_cases)]


async def resolve_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> Principal:
    """Authenticate with topic 23's substrate, then resolve the principal.

    The standard ``Authorization: Bearer`` header wins when present
    (it is the RFC's credential slot); ``x-api-key`` is the fallback for
    program callers. Every failed half — missing, malformed, unknown,
    expired, forged — raises the ONE 401 envelope, classified by the
    engine that checked it; only a verified credential reaches the
    resolver.
    """
    resolver = get_principal_resolver(request)
    if authorization is not None:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() != "bearer" or not value.strip():
            raise AppError(
                FailureKind.UNAUTHORIZED,
                "not authenticated — the Authorization header must carry "
                "'Bearer <token>'",
            )
        username, scopes = _token_service(request).require(value.strip())
        return await resolver.for_token(username, scopes)
    if x_api_key is not None:
        record = await _api_key_service(request).call(x_api_key)
        return resolver.for_key(record)
    raise AppError(FailureKind.UNAUTHORIZED, NOT_AUTHENTICATED_MESSAGE)


PrincipalDep = Annotated[Principal, Depends(resolve_principal)]


def _forbid(decision: Decision, principal: Principal, action: str) -> None:
    """Raise the standard 403 envelope with the decision's reason in details."""
    raise AppError(
        FailureKind.FORBIDDEN,
        f"forbidden — {action} denied for {principal.name!r}: {decision.reason}",
        details={
            "action": action,
            "principal": principal.name,
            "principalKind": principal.kind,
            "reason": decision.reason,
        },
    )


PermissionGuard = Callable[[Principal, PolicyEngine], Coroutine[Any, Any, Guarded]]
"""The collection guard's shape — the dependency require_permission builds."""

OwnerGuard = Callable[[str, Request, Principal, PolicyEngine], Coroutine[Any, Any, GuardedPost]]
"""The object guard's shape — the dependency require_owner_or builds."""


def require_permission(action: Action) -> PermissionGuard:
    """Factory: the collection-level guard — decide ``action`` with no object."""

    async def guard(principal: PrincipalDep, engine: EngineDep) -> Guarded:
        decision = engine.decide(principal, action)
        if not decision.allowed:
            _forbid(decision, principal, action)
        return Guarded(principal=principal, decision=decision)

    return guard


def require_owner_or(action: Action) -> OwnerGuard:
    """Factory: the object-level guard — owner of THIS resource, or the authority.

    Fetches the post first (a missing post is the shared 404 envelope the
    public read answers — existence before verdict), then decides with the
    ``OwnedResource`` in hand so own-reach grants can match ownership and
    any-reach grants can bypass it. The handler receives the verdict AND
    the post, so nothing is fetched twice.
    """

    async def guard(
        post_id: str, request: Request, principal: PrincipalDep, engine: EngineDep
    ) -> GuardedPost:
        result = get_posts_use_cases(request).get_post.execute(post_id)
        if isinstance(result, Err):
            raise result.failure
        post = result.value
        decision = engine.decide(
            principal, action, OwnedResource(kind="post", id=post.id, owner=post.author)
        )
        if not decision.allowed:
            _forbid(decision, principal, action)
        return GuardedPost(principal=principal, decision=decision, post=post)

    return guard
