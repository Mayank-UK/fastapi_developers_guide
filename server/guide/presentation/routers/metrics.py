"""Prometheus exposition: ``GET /metrics``.

The monitoring scrape target for the deployed VM: the DEFAULT collector
registry — the process collector (CPU time, memory, file descriptors)
and the Python platform collector — rendered in the Prometheus text
exposition format. The route is deliberately dependency-free and
stateless, the liveness-probe discipline ``/api/health`` set: a scraper
asking "what does this process look like" gets a byte-honest answer with
the format's own registered content type, never the JSON envelope. The
contract is the exposition format itself — a line protocol, not a shape
OpenAPI could describe — so the mount is ``include_in_schema=False``
(the GraphQL precedent: the document could only misdescribe it).
"""

from fastapi import APIRouter, Response
from prometheus_client import REGISTRY, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def read_metrics() -> Response:
    """Render the default registry in the Prometheus text exposition format."""
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
