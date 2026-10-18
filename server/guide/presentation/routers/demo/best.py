"""The best-practices checklist demo (topic 41, area ``best``).

Thin router (family invariant): one GET, pure payload, declared response
model. The engine in ``guide/domain/demos/`` drives real self-requests
through the running app and reads the repo this process lives in; the
router's only job is handing it the live ASGI callable and the honest
roots — the server tree (always readable) and the repo root only when
its marker file is actually mounted, so repo-root checks degrade to
honest manual rows instead of pretending.
"""

from typing import Final

from fastapi import APIRouter, Request

from guide.domain.demos.best_checklist import (
    BestChecklistPanel,
    build_best_checklist_payload,
    default_roots,
)

router = APIRouter(prefix="/api/demo/best", tags=["demo:best"])

CHECKLIST_PATH: Final = "/checklist"
"""The router's one path (prefix-relative) — the terminal companion names it."""


@router.get(CHECKLIST_PATH, response_model=BestChecklistPanel)
async def read_best_checklist(request: Request) -> BestChecklistPanel:
    """Serve the live self-audit: probes, file reads, honest manuals."""
    server_root, repo_root = default_roots()
    return await build_best_checklist_payload(
        app=request.app,
        server_root=server_root,
        repo_root=repo_root,
    )
