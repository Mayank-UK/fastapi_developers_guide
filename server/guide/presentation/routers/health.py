"""Liveness probe: ``GET /api/health``.

Deliberately dependency-free (no DB/redis ping) — it answers "is the process
up", not "are its dependencies up"; readiness splits arrive with the
observability topic. Demonstrates the house router shape: ``Annotated``
dependency injection, a declared ``response_model``, zero business logic.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from guide.core.config import AppConfig, get_config

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    """Wire shape of the health payload (the published OpenAPI contract)."""

    status: Literal["ok"]
    env: str


@router.get("/health", response_model=HealthResponse)
def read_health(config: Annotated[AppConfig, Depends(get_config)]) -> HealthResponse:
    """Report process liveness plus the environment it booted in."""
    return HealthResponse(status="ok", env=config.env)
