"""The env-inspector demo (topic 36, area ``env``): a live panel, no knobs.

Thin router (family invariant): one GET, pure payload, declared response
model. The panel is built from the REAL process-wide config (``get_config``
— the cached instance the whole app reads) and the scenario store's live
snapshot (the flags sub-panel); nothing here constructs config or state of
its own, so what the wire shows is exactly what the process is running
under — secrets already redacted before the payload exists.
"""

from typing import Final

from fastapi import APIRouter

from guide.core.config import get_config
from guide.core.scenario import ScenarioStoreDep
from guide.domain.demos.env_inspector import (
    EnvInspectorPanel,
    build_env_inspector_payload,
)

router = APIRouter(prefix="/api/demo/env", tags=["demo:env"])

PANEL_PATH: Final = ""
"""The router's one path (prefix-relative) — the terminal companion names it."""


@router.get(PANEL_PATH, response_model=EnvInspectorPanel)
async def read_env_inspector(store: ScenarioStoreDep) -> EnvInspectorPanel:
    """Serve the live inspector: settings + sources, redacted secrets, flags."""
    return build_env_inspector_payload(get_config(), store.get())
