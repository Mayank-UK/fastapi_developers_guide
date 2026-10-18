"""Demo scenario API: ``GET``/``PATCH /api/demo/scenario``.

Thin router over the app's ScenarioStore: GET returns the current snapshot;
PATCH applies a partial update (missing keys mean unchanged). Invalid enum
values never reach the store — FastAPI rejects the body as a
RequestValidationError, which the shared handlers render as the 422
validation_failed envelope.
"""

from fastapi import APIRouter

from guide.core.scenario import ScenarioPatch, ScenarioState, ScenarioStoreDep

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/scenario", response_model=ScenarioState)
def read_scenario(store: ScenarioStoreDep) -> ScenarioState:
    """Report the current demo scenario."""
    return store.get()


@router.patch("/scenario", response_model=ScenarioState)
def update_scenario(patch: ScenarioPatch, store: ScenarioStoreDep) -> ScenarioState:
    """Apply a partial update; the response is the resulting full state."""
    return store.update(patch)
