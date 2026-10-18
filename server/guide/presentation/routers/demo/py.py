"""Python-language demo API: ``GET /api/demo/py/runtime-types``.

Thin router (family invariant): the endpoint declares its response model
and delegates to the pure builder in ``guide.domain.demos.runtime_types`` —
no introspection logic lives here. The payload proves, on real guide
objects, that annotations are metadata the interpreter never enforces.
"""

from fastapi import APIRouter

from guide.domain.demos.runtime_types import RuntimeTypesPayload, build_runtime_types_payload

router = APIRouter(prefix="/api/demo/py", tags=["demo:py"])


@router.get("/runtime-types", response_model=RuntimeTypesPayload)
def read_runtime_types() -> RuntimeTypesPayload:
    """Serve the runtime-typing proof payload (pure builder, no state)."""
    return build_runtime_types_payload()
