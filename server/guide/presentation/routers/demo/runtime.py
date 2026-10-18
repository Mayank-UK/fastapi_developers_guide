"""Python-runtime demo API: measured async timing + NDJSON streaming.

Thin routers (family invariant). ``/async`` awaits the pure measurement
builder and declares its response model. ``/streaming`` returns a
``StreamingResponse`` wrapping a REAL async generator — with
``response_model`` deliberately not set: the body is a stream of NDJSON
lines, not one JSON document, so there is no single model for FastAPI to
serialize; each line is a typed ``StreamChunk`` the generator encodes
itself, and ``StreamingResponse`` sends each line as it is produced.
"""

from typing import Final

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from guide.domain.demos.runtime_async import AsyncTimingPayload, build_async_timing_payload
from guide.domain.demos.runtime_streaming import stream_runtime_chunks

router = APIRouter(prefix="/api/demo/runtime", tags=["demo:runtime"])

NDJSON_MEDIA_TYPE: Final = "application/x-ndjson"


@router.get("/async", response_model=AsyncTimingPayload)
async def read_async_timing() -> AsyncTimingPayload:
    """Serve the measured sequential-vs-gathered timing payload."""
    return await build_async_timing_payload()


@router.get("/streaming")
async def read_streaming() -> StreamingResponse:
    """Stream the async generator's chunks as NDJSON lines, as produced."""
    return StreamingResponse(stream_runtime_chunks(), media_type=NDJSON_MEDIA_TYPE)
