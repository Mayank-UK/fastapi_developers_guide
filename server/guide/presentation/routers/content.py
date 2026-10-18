"""Content API: ``GET /api/content`` + ``GET /api/content/{topic_id}``.

Thin router (family invariant): resolve the registry from app.state, shape
the response, done — no business logic. The registry itself was validated
once at construction (import time); an unknown topic id raises AppError
which the shared handlers render as the 404 envelope.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from guide.content.models import (
    CONTENT_API_VERSION,
    ContentDetail,
    ContentListResponse,
)
from guide.content.registry import ContentRegistry
from guide.core.errors import AppError, FailureKind

router = APIRouter(prefix="/api/content", tags=["content"])


def get_content_registry(request: Request) -> ContentRegistry:
    """FastAPI dependency: the validated registry wired in create_app."""
    registry = request.app.state.content_registry
    if not isinstance(registry, ContentRegistry):
        raise AppError(FailureKind.INTERNAL, "Content registry not wired on app.state")
    return registry


@router.get("", response_model=ContentListResponse, response_model_exclude_none=True)
def list_content(
    registry: Annotated[ContentRegistry, Depends(get_content_registry)],
) -> ContentListResponse:
    """Serve the whole topic index: groups then topics, each sorted by order."""
    return ContentListResponse(
        version=CONTENT_API_VERSION,
        groups=sorted(registry.groups(), key=lambda group: group.order),
        topics=sorted(registry.summaries(), key=lambda summary: summary.order),
    )


@router.get("/{topic_id}", response_model=ContentDetail, response_model_exclude_none=True)
def read_topic(
    topic_id: str,
    registry: Annotated[ContentRegistry, Depends(get_content_registry)],
) -> ContentDetail:
    """Serve one topic's full payload + version; unknown ids are the 404 envelope."""
    topic = registry.topic_by_id(topic_id)
    if topic is None:
        raise AppError(FailureKind.NOT_FOUND, f"Topic '{topic_id}' not found")
    return ContentDetail.model_validate({**topic.model_dump(), "version": CONTENT_API_VERSION})
