"""The files workbench demo: topic 26's live lab (area ``files``).

Thin routers (family invariant): every decision — cap, sniff agreement,
sanitizing, range resolution, image decoding — lives in the domain service;
this file parses multipart bodies, reads headers and query params, calls
``FilesWorkbenchService``, and maps results onto responses. Binary
responses (downloads) and the streamed response (backpressure) are the two
places this router builds responses by hand, which is exactly what
``Response``/``StreamingResponse`` exist for.

Endpoint map (prefix ``/api/demo/files``):

- ``GET  /``          — the panel: real policy, stored rows, tour map
- ``POST /upload``    — multipart upload (cap + sniff, server-minted id)
- ``GET  /stored``    — inspect what survived, both names on display
- ``GET  /{file_id}/download?mode=inline|attachment`` — Content-Disposition
- ``GET  /{file_id}/download`` + ``Range`` header or ``?bytes=0-99`` — 206
- ``POST /images``    — Pillow round: thumbnail + grayscale variants
- ``POST /traversal`` — one hostile name against the naming defense
- ``GET  /stream``    — paced chunks over StreamingResponse
"""

from typing import Annotated, Final, Literal

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from guide.core.errors import AppError, FailureKind
from guide.domain.demos.files_workbench import (
    STREAM_MEDIA_TYPE,
    FilesWorkbenchPanel,
    ImageVariantsRow,
    StoredFilesRow,
    StreamPlan,
    TraversalRequest,
    TraversalRow,
    UploadOutcomeRow,
    build_chunk_plan,
    build_files_workbench_panel,
    build_image_variants_row,
    build_stored_file_row,
    build_traversal_row,
    build_upload_outcome_row,
    paced_chunks,
)
from guide.domain.files.disposition import build_content_disposition
from guide.domain.files.ranges import RANGE_UNIT
from guide.domain.files.service import FilesWorkbenchService
from guide.domain.files.storage import StoredFile
from guide.domain.files.validation import GENERIC_CONTENT_TYPE

router = APIRouter(prefix="/api/demo/files", tags=["demo:files"])

PANEL_PATH: Final = ""
UPLOAD_ROUTE: Final = "/upload"
STORED_ROUTE: Final = "/stored"
DOWNLOAD_ROUTE: Final = "/{file_id}/download"
IMAGES_ROUTE: Final = "/images"
TRAVERSAL_ROUTE: Final = "/traversal"
STREAM_ROUTE: Final = "/stream"
"""The routers' paths (prefix-relative) — the terminal companion names them."""

ACCEPT_RANGES: Final[str] = RANGE_UNIT
"""Every download answer advertises ``Accept-Ranges: bytes``."""

DispositionMode = Literal["inline", "attachment"]


def get_workbench_service(request: Request) -> FilesWorkbenchService:
    """FastAPI dependency: the workbench service (wired in create_app)."""
    service = request.app.state.files_workbench
    if not isinstance(service, FilesWorkbenchService):
        raise AppError(FailureKind.INTERNAL, "files workbench service not wired on app.state")
    return service


ServiceDep = Annotated[FilesWorkbenchService, Depends(get_workbench_service)]


def _named_upload(file: UploadFile) -> tuple[str, str]:
    """Unwrap the multipart part's honest parts: a name and a declared type.

    A part without a filename is not a file upload (plain multipart text
    fields arrive that way) — the standard 422, not a crash on None. A part
    without a content type declares nothing, which the validator treats as
    the generic no-claim type.
    """
    if not file.filename:
        raise AppError(
            FailureKind.VALIDATION_FAILED,
            "upload rejected — the multipart part carries no filename",
        )
    return file.filename, file.content_type or GENERIC_CONTENT_TYPE


def _download_headers(record: StoredFile, mode: DispositionMode) -> dict[str, str]:
    """The headers every download carries: disposition + range advertisement."""
    return {
        "Content-Disposition": build_content_disposition(mode, record.display_name),
        "Accept-Ranges": ACCEPT_RANGES,
    }


@router.get(PANEL_PATH, response_model=FilesWorkbenchPanel)
async def read_files_workbench_panel(service: ServiceDep) -> FilesWorkbenchPanel:
    """The workbench panel: policy, stored rows, endpoints, honesty notes."""
    return build_files_workbench_panel(service)


@router.post(UPLOAD_ROUTE, response_model=UploadOutcomeRow)
async def upload_file(service: ServiceDep, file: Annotated[UploadFile, File()]) -> UploadOutcomeRow:
    """Accept one multipart upload: streamed cap check, sniff, minted id."""
    display_name, declared_type = _named_upload(file)
    outcome = await service.upload(display_name, declared_type, file.read)
    return build_upload_outcome_row(outcome)


@router.get(STORED_ROUTE, response_model=StoredFilesRow)
async def list_stored_files(service: ServiceDep) -> StoredFilesRow:
    """Inspect the store: every row with both names and the sniff verdict."""
    records = service.store.list_files()
    return StoredFilesRow(
        count=len(records),
        files=[build_stored_file_row(record) for record in records],
    )


@router.get(DOWNLOAD_ROUTE)
async def download_stored_file(
    file_id: str,
    service: ServiceDep,
    mode: Annotated[DispositionMode, Query()] = "attachment",
    range_header: Annotated[str | None, Header(alias="Range")] = None,
    bytes_window: Annotated[str | None, Query(alias="bytes")] = None,
) -> Response:
    """Serve one stored file — full (200), or one window as a 206 + Content-Range.

    The window may arrive as the RFC's ``Range`` header (curl ``-H``) or as
    the ``?bytes=0-99`` query form (browser-visible); the header wins when
    both are present. Invalid or unsatisfiable windows answer the 422
    envelope from the service (the taught divergence from HTTP's 416).
    """
    header_range = range_header.strip() if range_header else None
    effective_range = header_range or (
        f"{RANGE_UNIT}={bytes_window}" if bytes_window else None
    )
    if effective_range is None:
        record, body = service.download(file_id)
        return Response(
            content=body,
            media_type=record.sniffed_type,
            headers=_download_headers(record, mode),
        )
    ranged = service.ranged_download(file_id, effective_range)
    assert ranged is not None, "a non-empty range never takes the no-range path"
    record, slice_body, resolved = ranged
    return Response(
        content=slice_body,
        status_code=206,
        media_type=record.sniffed_type,
        headers={"Content-Range": resolved.content_range, **_download_headers(record, mode)},
    )


@router.post(IMAGES_ROUTE, response_model=ImageVariantsRow)
async def process_image(
    service: ServiceDep, file: Annotated[UploadFile, File()]
) -> ImageVariantsRow:
    """The Pillow round: upload + decode + thumbnail + grayscale variants."""
    display_name, declared_type = _named_upload(file)
    variants = await service.image_variants(display_name, declared_type, file.read)
    return build_image_variants_row(variants)


@router.post(TRAVERSAL_ROUTE, response_model=TraversalRow)
async def test_traversal_name(
    request: TraversalRequest, service: ServiceDep
) -> TraversalRow:
    """Run one submitted name through the whole naming defense, for show."""
    return build_traversal_row(service.traversal_verdict(request.name))


@router.get(STREAM_ROUTE)
async def stream_paced_chunks(
    chunks: Annotated[int, Query(ge=1, le=64)] = 8,
    chunk_bytes: Annotated[int, Query(alias="chunkBytes", ge=64, le=4096)] = 1024,
    pace_ms: Annotated[int, Query(alias="paceMs", ge=0, le=1000)] = 300,
) -> StreamingResponse:
    """The backpressure stream: paced chunks over one async generator.

    Each chunk is one newline-delimited JSON line, byte-padded to the
    promised size; the pacing is a labeled simulation (a slow client pauses
    this generator for free). The x-* headers state the plan so the client
    can verify each chunk against it.
    """
    plan: StreamPlan = build_chunk_plan(chunks, chunk_bytes, pace_ms)
    return StreamingResponse(
        paced_chunks(plan),
        media_type=STREAM_MEDIA_TYPE,
        headers={
            "x-chunk-count": str(plan.chunk_count),
            "x-chunk-bytes": str(plan.chunk_bytes),
            "x-pace-ms": str(plan.pace_ms),
            "x-total-bytes": str(plan.total_bytes),
            "Cache-Control": "no-store",
        },
    )
