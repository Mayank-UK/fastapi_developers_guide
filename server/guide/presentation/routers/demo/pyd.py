"""Pydantic demo API: ``GET /api/demo/pyd/lab/schema`` + ``POST …/validate``.

Thin routers (family invariant): the handlers declare their response models
and delegate to the pure builders in ``guide.domain.demos.pyd_lab``. The
POST body is the lab's permissive ``LabRequest`` — bodies that cannot parse
into it (a non-list ``tags``, a non-string ``handle``, a missing field) are
refused by FastAPI's own 422 envelope before the handler runs, which is
exactly the validation-at-the-boundary behavior the demo teaches.
"""

from fastapi import APIRouter

from guide.domain.demos.pyd_lab import (
    LabRequest,
    PydLabReportPayload,
    PydLabSchemaPayload,
    build_schema_payload,
    build_validation_report,
)

router = APIRouter(prefix="/api/demo/pyd", tags=["demo:pyd"])


@router.get("/lab/schema", response_model=PydLabSchemaPayload)
def read_lab_schema() -> PydLabSchemaPayload:
    """Serve the specimen model's generated JSON Schema."""
    return build_schema_payload()


@router.post("/lab/validate", response_model=PydLabReportPayload, response_model_exclude_none=True)
def validate_lab_submission(body: LabRequest) -> PydLabReportPayload:
    """Report, per field, what pydantic's lax pipeline does with the body."""
    return build_validation_report(body)
