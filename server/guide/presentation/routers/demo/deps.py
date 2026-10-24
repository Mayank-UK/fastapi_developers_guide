"""The deps-manifest demo (topic 31, area ``deps``): a live panel, no knobs.

Thin router (family invariant): one GET, pure payload, declared response
model. The panel is parsed at request time from the REAL server/pyproject.toml
and server/uv.lock — the two files the running server was itself built from
(they live inside server/, so the bind-mounted container reads them; the
env-inspector precedent of introspecting real files). Nothing here restates a
version: relock the project and the panel changes with it.
"""

from fastapi import APIRouter

from guide.domain.demos.dep_manifest import DepsManifestPanel, build_dep_manifest_payload

router = APIRouter(prefix="/api/demo/deps", tags=["demo:deps"])

PANEL_PATH = ""
"""The router's one path (prefix-relative) — the terminal companion names it."""


@router.get(PANEL_PATH, response_model=DepsManifestPanel)
async def read_dep_manifest() -> DepsManifestPanel:
    """Serve the live manifest panel: groups, pins vs ranges, drift, tree."""
    return build_dep_manifest_payload()
