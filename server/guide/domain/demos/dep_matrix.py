"""Dep-matrix demo: the flavor objects + identity proofs, pure builders.

``GET /api/demo/dep/matrix`` resolves a whole matrix of dependency flavors
in ONE request (the ``Depends`` wiring lives in
``guide.presentation.dependencies.demo_flavors``); this module holds the
flavor value objects those providers return, the ``identity_token``
derivation, and the pure row builder. Identity is observable because every
flavor object carries an ``identity_token`` — ``id()``-derived, stable
while the request holds the object alive, and equal exactly when the
framework handed two parameters the SAME instance:

- cached (``use_cache=True``, the default): one provider run per request —
  tokens for repeated ``Depends`` of the same callable are EQUAL;
- ``use_cache=False``: the provider re-runs per parameter — tokens DIFFER;
- a sub-dependency chain shares nodes with the handler's direct requests
  wherever the cache key (the callable) is the same.

The sync-in-async row reports thread names, not object ids: a sync provider
resolved by an async endpoint runs on a threadpool worker while the handler
itself runs on the event loop's thread — the verdict is derived from the
two names, never asserted.

Everything here is framework-free by construction: plain classes and a pure
builder — no I/O, no state, no fastapi imports.
"""

import threading
from typing import Literal
from uuid import uuid4

from guide.core.serialization import CamelModel

MatrixFlavor = Literal[
    "function",
    "callable-class",
    "cached-x2",
    "uncached-x2",
    "chain-depth-3",
    "sync-in-async",
]

MatrixVerdict = Literal[
    "single",
    "same-instance",
    "distinct-instances",
    "shared-middle",
    "threadpool",
    "event-loop",
]


def identity_token(obj: object) -> str:
    """Stable-while-alive identity token: class name + ``id()`` in hex.

    Within one request the resolved objects stay referenced, so tokens are
    stable and distinct instances get distinct tokens; two parameters see
    the same instance exactly when their tokens are equal.
    """
    return f"{type(obj).__name__}#{id(obj):x}"


class Correlation:
    """Function-dep flavor: one correlation context per request (cached)."""

    @property
    def token(self) -> str:
        """This instance's identity token — the same string all request long."""
        return identity_token(self)


class RateBudget:
    """Cached-x2 flavor: a request-scoped budget any handler parameter may claim."""

    @property
    def token(self) -> str:
        """Identity token: two ``Depends(get_rate_budget)`` parameters see one instance."""
        return identity_token(self)


class Cursor:
    """Uncached flavor: a fresh cursor is exactly what you never cache."""

    @property
    def token(self) -> str:
        """Identity token: every ``use_cache=False`` resolution is a new instance."""
        return identity_token(self)


class ParsedToken:
    """Chain depth 1 (base): the parsed credential every actor is built from."""

    @property
    def token(self) -> str:
        return identity_token(self)


class AuthenticatedActor:
    """Chain depth 2 (middle): an actor, holding the token it was built from."""

    def __init__(self, token_credential: ParsedToken) -> None:
        self.token_credential = token_credential

    @property
    def token(self) -> str:
        return identity_token(self)


class VerifiedRequest:
    """Chain depth 3 (top): the verified request, holding its actor."""

    def __init__(self, actor: AuthenticatedActor) -> None:
        self.actor = actor

    @property
    def token(self) -> str:
        return identity_token(self)


class ApiKey:
    """What the callable-class provider mints per request."""

    def __init__(self, value: str, issuer_token: str) -> None:
        self.value = value
        self.issuer_token = issuer_token


class ApiKeyIssuer:
    """Callable-class flavor: FastAPI calls the instance like a function.

    The provider object lives at module scope (one per process — where
    configuration belongs); ``__call__`` runs per request and mints a fresh
    key, carrying both identities so the demo can show provider-vs-product.
    """

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def __call__(self) -> ApiKey:
        """Mint one key: the per-request product of a process-wide provider."""
        return ApiKey(
            value=f"{self._prefix}-{uuid4().hex[:8]}",
            issuer_token=identity_token(self),
        )


class ThreadView:
    """Sync-dep flavor evidence: the thread the PROVIDER ran on."""

    def __init__(self) -> None:
        self.thread_name = threading.current_thread().name


class MatrixRow(CamelModel):
    """One flavor's identity proof; wire is camelCase."""

    flavor: MatrixFlavor
    label: str
    tokens: list[str]
    """Identity tokens in resolution order (or thread names for the sync row)."""

    verdict: MatrixVerdict


class DepMatrixPayload(CamelModel):
    """Wire shape of ``GET /api/demo/dep/matrix`` (camelCase)."""

    rows: list[MatrixRow]


def build_matrix_payload(
    correlation: Correlation,
    budget_a: RateBudget,
    budget_b: RateBudget,
    cursor_a: Cursor,
    cursor_b: Cursor,
    verified: VerifiedRequest,
    actor_direct: AuthenticatedActor,
    api_key: ApiKey,
    thread_view: ThreadView,
    handler_thread: str,
) -> DepMatrixPayload:
    """Derive every flavor's proof from the objects ONE request resolved."""
    actor = verified.actor
    base = actor.token_credential
    rows = [
        MatrixRow(
            flavor="function",
            label="plain function: asked once, cached for the whole request",
            tokens=[correlation.token],
            verdict="single",
        ),
        MatrixRow(
            flavor="callable-class",
            label="__call__ instance: provider at module scope, minted per request",
            tokens=[api_key.issuer_token, api_key.value],
            verdict="single",
        ),
        MatrixRow(
            flavor="cached-x2",
            label="same dependency asked twice (use_cache=True default)",
            tokens=[budget_a.token, budget_b.token],
            verdict="same-instance" if budget_a.token == budget_b.token else "distinct-instances",
        ),
        MatrixRow(
            flavor="uncached-x2",
            label="use_cache=False: the provider re-runs per parameter",
            tokens=[cursor_a.token, cursor_b.token],
            verdict="distinct-instances" if cursor_a.token != cursor_b.token else "same-instance",
        ),
        MatrixRow(
            flavor="chain-depth-3",
            label="top → middle → base; the handler also asks the middle directly",
            tokens=[verified.token, actor.token, base.token, actor_direct.token],
            verdict="shared-middle" if actor.token == actor_direct.token else "distinct-instances",
        ),
        MatrixRow(
            flavor="sync-in-async",
            label="sync provider inside an async endpoint: threadpool vs event loop",
            tokens=[
                f"dep-thread:{thread_view.thread_name}",
                f"handler-thread:{handler_thread}",
            ],
            verdict=("threadpool" if thread_view.thread_name != handler_thread else "event-loop"),
        ),
    ]
    return DepMatrixPayload(rows=rows)
