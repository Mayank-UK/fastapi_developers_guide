"""The deploy-stack demo (topic 37, area ``deploy``).

Thin router (family invariant): one GET, the payload builder does the
work, a declared response model. The panel inspects the repo's REAL
deploy surface — the compose trio's services and rails, the Dockerfiles,
the CI/deploy workflows, the env template — plus the runtime facts this
process always has (env mode, interpreter, command line, a REAL internal
``GET /api/health``). Repo-root checks run for real when the repo is
mounted (tests + the dev container) and degrade to honest manual rows on
the live server container, whose bind mount is ``server/`` only.
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request

from guide.core.config import AppConfig, get_config
from guide.domain.demos.deploy_stack import (
    DeployStackPanel,
    build_deploy_stack_payload,
    default_roots,
)

router = APIRouter(prefix="/api/demo/deploy", tags=["demo:deploy"])

STACK_PATH: Final = "/stack"
"""The router's one path (prefix-relative) — the terminal companion names it."""


@router.get(STACK_PATH, response_model=DeployStackPanel)
async def read_deploy_stack_panel(
    request: Request,
    config: Annotated[AppConfig, Depends(get_config)],
) -> DeployStackPanel:
    """Serve the live deploy panel: runtime facts, file checks, honest manuals."""
    server_root, repo_root = default_roots()
    return await build_deploy_stack_payload(
        app=request.app,
        config=config,
        server_root=server_root,
        repo_root=repo_root,
    )
