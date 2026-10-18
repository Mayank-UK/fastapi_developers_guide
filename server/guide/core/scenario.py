"""Runtime-switchable demo scenario: data mode + failure injection.

Demos must behave identically against fake in-memory data and (from Phase 6
on) live stores, and must be able to demonstrate failure paths on demand —
``ScenarioStore`` is the single runtime toggle the demo endpoints read.
State snapshots (``ScenarioState``) are frozen and validated; updates build
a NEW snapshot by merging the patch into the current one and re-running
pydantic validation, so the store defends its own enum invariant even when
called with untyped input. The store instance lives on ``app.state.scenario``
(one per app — tests get per-app isolation); ``get_scenario_store`` is the
FastAPI dependency routers use to reach it.
"""

from typing import Annotated, Literal

from fastapi import Depends, Request

from guide.core.errors import AppError, FailureKind
from guide.core.serialization import CamelModel

DataMode = Literal["fake", "live"]
FailureInjection = Literal["none", "error", "latency"]

DEFAULT_DATA_MODE: DataMode = "fake"
DEFAULT_FAILURE_INJECTION: FailureInjection = "none"


class ScenarioState(CamelModel):
    """Immutable snapshot of the demo scenario; wire is camelCase."""

    data_mode: DataMode = DEFAULT_DATA_MODE
    inject_failure: FailureInjection = DEFAULT_FAILURE_INJECTION


class ScenarioPatch(CamelModel):
    """Partial update body for PATCH /api/demo/scenario.

    Missing keys mean "unchanged" (never None-as-value) — the store merges
    with ``model_dump(exclude_unset=True)``.
    """

    data_mode: DataMode | None = None
    inject_failure: FailureInjection | None = None


class ScenarioStore:
    """Holds the current ScenarioState; get / partial-update / reset."""

    def __init__(self, initial: ScenarioState | None = None) -> None:
        """Start from the given state or the documented defaults."""
        self._initial = initial if initial is not None else ScenarioState()
        self._state = self._initial

    def get(self) -> ScenarioState:
        """Return the current state snapshot."""
        return self._state

    def update(self, patch: ScenarioPatch) -> ScenarioState:
        """Merge only the fields the patch set, revalidating the enums.

        Raises ``AppError(validation_failed)`` if the merged state is not a
        legal ScenarioState — the store defends its own invariant because
        patches can also arrive from untyped callers, not just HTTP bodies
        (which FastAPI pre-validates).
        """
        changes = patch.model_dump(exclude_unset=True)
        try:
            self._state = ScenarioState.model_validate(
                {**self._state.model_dump(), **changes}
            )
        except ValueError as exc:
            raise AppError(
                FailureKind.VALIDATION_FAILED, f"Invalid scenario patch: {exc}"
            ) from exc
        return self._state

    def reset(self) -> None:
        """Return to the state the store was constructed with."""
        self._state = self._initial


def get_scenario_store(request: Request) -> ScenarioStore:
    """FastAPI dependency: the app's scenario store (wired in create_app)."""
    store = request.app.state.scenario
    if not isinstance(store, ScenarioStore):
        raise AppError(FailureKind.INTERNAL, "Scenario store not wired on app.state")
    return store


ScenarioStoreDep = Annotated[ScenarioStore, Depends(get_scenario_store)]
