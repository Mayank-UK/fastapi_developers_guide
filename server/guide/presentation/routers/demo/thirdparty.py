"""The third-party hub demo (topic 42, area ``thirdparty``).

Thin router (family invariant): one GET, the payload builder does the
work, a declared response model. The panel serves the integrate-vs-build
walk (verified against the manifest and the server tree at request
time), the real integration inventory (backing services, machine auth,
the deploy pipeline's artifact channels), the key/secret surface as
names with blast radii — values are never read, so the wire cannot carry
one — and the real quotas (live reads off the composition root beside
the domain's declared constants). Repo-root evidence degrades honestly
on the live server container, whose bind mount is ``server/`` only.
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request

from guide.core.config import AppConfig, get_config
from guide.core.errors import AppError, FailureKind
from guide.domain.demos.thirdparty_hub import (
    LiveQuotaFacts,
    ThirdPartyHubPanel,
    build_third_party_hub,
    default_roots,
)
from guide.domain.security.rate_limit import SlidingWindowLimiter
from guide.presentation.dependencies.rate_limit import get_rate_limiter

router = APIRouter(prefix="/api/demo/thirdparty", tags=["demo:thirdparty"])

HUB_PATH: Final = "/hub"
"""The router's one path (prefix-relative) — the terminal companion names it."""


def _quota_facts(
    request: Request, limiter: Annotated[SlidingWindowLimiter, Depends(get_rate_limiter)]
) -> LiveQuotaFacts:
    """Snapshot the live quota facts off the composition root — counters only, no I/O.

    The limiter's policy (budget, window, keying) and the engine pool's
    size are the two quotas this process can read live; everything else
    on the quotas panel is a declared domain constant the builder imports.
    """
    pool_size = getattr(request.app.state.db_engine.pool, "size", None)
    if not callable(pool_size):
        raise AppError(FailureKind.INTERNAL, "Engine pool not wired on app.state")
    return LiveQuotaFacts(
        rate_policy=(
            f"{limiter.policy.budget} hits / {limiter.policy.window_s:g}s "
            f"per {limiter.policy.keying}"
        ),
        pool_size=int(pool_size()),
    )


QuotaFactsDep = Annotated[LiveQuotaFacts, Depends(_quota_facts)]


@router.get(HUB_PATH, response_model=ThirdPartyHubPanel)
async def read_third_party_hub_panel(
    request: Request,
    config: Annotated[AppConfig, Depends(get_config)],
    quotas: QuotaFactsDep,
) -> ThirdPartyHubPanel:
    """Serve the third-party hub: decisions, integrations, secrets, quotas."""
    server_root, repo_root = default_roots()
    return build_third_party_hub(
        server_root=server_root,
        repo_root=repo_root,
        config=config,
        quotas=quotas,
    )
