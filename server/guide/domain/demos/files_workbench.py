"""The files workbench demo payload: the panel + outcome rows + the stream.

Demo ``files:workbench`` (topic 26, INLINE in the UploadFile section): the
workbench's upload panel IS the live lesson, so this module shapes
everything the panel shows — the policy (cap, chunked-read size, thumbnail
box), the stored-file rows, and the outcome rows for upload / image
variants / traversal. All pure shaping over the real service's entities;
no logic lives here that the service didn't already decide.

The backpressure half is the one piece of mechanics: ``build_chunk_plan``
validates a stream configuration into a concrete plan (N chunks of B
newline-delimited JSON bytes, padded exactly to B), and ``paced_chunks``
turns a plan into the async generator a StreamingResponse consumes — one
``asyncio.sleep(pace_ms)`` between chunks. The pacing is SIMULATED and
labeled as such everywhere it appears: it stands in for what a genuinely
slow client does to this generator for free (a client that stops reading
stops the ASGI send, which stops the generator's next iteration — the
sleep just makes the pause visible on a fast loopback client).
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.files.images import THUMBNAIL_MAX_EDGE
from guide.domain.files.service import (
    READ_CHUNK_BYTES,
    FilesWorkbenchService,
    ImageVariants,
    TraversalVerdict,
    UploadOutcome,
)
from guide.domain.files.storage import StoredFile
from guide.domain.files.validation import MAX_UPLOAD_BYTES

UPLOAD_PATH: Final = "/api/demo/files/upload"
STORED_PATH: Final = "/api/demo/files/stored"
DOWNLOAD_PATH: Final = "/api/demo/files/{fileId}/download"
IMAGES_PATH: Final = "/api/demo/files/images"
TRAVERSAL_PATH: Final = "/api/demo/files/traversal"
STREAM_PATH: Final = "/api/demo/files/stream"
"""The workbench's endpoints — the panel and the terminal companion name them."""

SPOOL_THRESHOLD_BYTES: Final[int] = 1024 * 1024
"""Starlette's SpooledTemporaryFile rollover point: 1 MiB in RAM, then disk."""

STREAM_MIN_CHUNKS: Final[int] = 1
STREAM_MAX_CHUNKS: Final[int] = 64
STREAM_MIN_CHUNK_BYTES: Final[int] = 64
STREAM_MAX_CHUNK_BYTES: Final[int] = 4096
STREAM_MIN_PACE_MS: Final[int] = 0
STREAM_MAX_PACE_MS: Final[int] = 1000
"""The stream endpoint's knobs and their bounds (FastAPI query constraints)."""

STREAM_MEDIA_TYPE: Final[str] = "application/x-ndjson"
"""Newline-delimited JSON: one line per chunk, parseable as chunks arrive."""


class FilesPolicyRow(CamelModel):
    """The workbench's real numbers: what uploads and variants are bounded by."""

    max_upload_bytes: int
    read_chunk_bytes: int
    spool_threshold_bytes: int
    thumbnail_max_edge: int


class StoredFileRow(CamelModel):
    """One stored file's metadata — both names on display, sniff beside claim."""

    file_id: str
    display_name: str
    sanitized_name: str
    declared_type: str
    sniffed_type: str
    size_bytes: int
    stored_at: str


class EndpointRow(CamelModel):
    """One workbench endpoint: the path and what trying it teaches."""

    path: str
    method: str
    teaches: str


class FilesWorkbenchPanel(CamelModel):
    """Wire shape of ``GET /api/demo/files`` — the workbench panel's contract."""

    policy: FilesPolicyRow
    stored_files: list[StoredFileRow]
    endpoints: list[EndpointRow]
    honesty_notes: list[str]
    reasoning: str


class StoredFilesRow(CamelModel):
    """Wire shape of ``GET /api/demo/files/stored`` — the store's inventory."""

    count: int
    files: list[StoredFileRow]


class TraversalRequest(CamelModel):
    """Wire shape of the traversal tester's body: one hostile name, nothing else."""

    name: str


class SniffRow(CamelModel):
    """The verdict that admitted (or would reject) a body: claim vs bytes."""

    declared_type: str
    sniffed_type: str
    agrees: bool
    note: str


class UploadOutcomeRow(CamelModel):
    """Wire shape of one accepted upload: the stored row + the sniff verdict."""

    file: StoredFileRow
    sniff: SniffRow
    detail: str


class ImageVariantsRow(CamelModel):
    """Wire shape of the image round: facts, variants as data URLs, sizes."""

    file: StoredFileRow
    sniff: SniffRow
    width: int
    height: int
    decoded_format: str
    thumbnail_data_url: str
    grayscale_data_url: str
    thumbnail_bytes: int
    grayscale_bytes: int
    detail: str


class TraversalRow(CamelModel):
    """Wire shape of one hostile name's trip through the naming defense."""

    submitted_name: str
    sanitized_name: str | None
    accepted: bool
    storage_key: str
    naive_join_target: str
    containment_holds: bool
    verdict: str


class StreamPlan(CamelModel):
    """One stream round's concrete plan: how many chunks, how big, how paced."""

    chunk_count: int
    chunk_bytes: int
    pace_ms: int
    total_bytes: int
    pacing_note: str


class StreamChunk(CamelModel):
    """One JSON line of the stream: identity, size, padding-honest."""

    chunk: int
    of: int
    bytes: int


def build_stored_file_row(record: StoredFile) -> StoredFileRow:
    """Shape one stored-file row (ISO-8601 UTC timestamp on the wire)."""
    return StoredFileRow(
        file_id=record.file_id,
        display_name=record.display_name,
        sanitized_name=record.sanitized_name,
        declared_type=record.declared_type,
        sniffed_type=record.sniffed_type,
        size_bytes=record.size_bytes,
        stored_at=record.stored_at.isoformat(),
    )


def build_files_workbench_panel(service: FilesWorkbenchService) -> FilesWorkbenchPanel:
    """Shape the panel: real policy constants, live stored rows, the tour map."""
    stored = [build_stored_file_row(record) for record in service.store.list_files()]
    return FilesWorkbenchPanel(
        policy=FilesPolicyRow(
            max_upload_bytes=MAX_UPLOAD_BYTES,
            read_chunk_bytes=READ_CHUNK_BYTES,
            spool_threshold_bytes=SPOOL_THRESHOLD_BYTES,
            thumbnail_max_edge=THUMBNAIL_MAX_EDGE,
        ),
        stored_files=stored,
        endpoints=[
            EndpointRow(
                path=UPLOAD_PATH,
                method="POST",
                teaches="multipart upload — cap enforced while the stream is read",
            ),
            EndpointRow(
                path=STORED_PATH,
                method="GET",
                teaches="what survived: metadata with both names and the sniff verdict",
            ),
            EndpointRow(
                path=DOWNLOAD_PATH,
                method="GET",
                teaches="Content-Disposition inline vs attachment, RFC 6266/5987 names",
            ),
            EndpointRow(
                path=DOWNLOAD_PATH + " + Range: bytes=0-99",
                method="GET",
                teaches="one window of the file: 206 + Content-Range, or 422 when invalid",
            ),
            EndpointRow(
                path=IMAGES_PATH,
                method="POST",
                teaches="Pillow round: decode, thumbnail, grayscale — re-encoded PNG",
            ),
            EndpointRow(
                path=TRAVERSAL_PATH,
                method="POST",
                teaches="the ../ family against the allow-list and containment check",
            ),
            EndpointRow(
                path=STREAM_PATH,
                method="GET",
                teaches="chunked streaming with paced chunks — watch each chunk arrive",
            ),
        ],
        honesty_notes=[
            "the store is IN MEMORY and demo-scoped: a server restart loses every "
            "stored file (the port is the seam a disk or S3 adapter would fill)",
            "over-cap uploads, MIME disagreements, invalid ranges, and hostile names "
            "all answer the ONE validation_failed 422 envelope — the deliberate "
            "divergence from HTTP's 413/416, taught in the range section",
            "the stream's pacing is SIMULATED server-side sleep — a genuinely slow "
            "client produces the same pauses for free, because the generator only "
            "advances when the previous chunk was sent",
        ],
        reasoning=(
            "Uploads are streams that get validated WHILE they are read (never fully "
            "buffered first), stored under server-minted ids with the user's name kept "
            "as data, and served back with explicit Content-Disposition — plus ranges, "
            "Pillow variants, and a paced stream that makes backpressure visible."
        ),
    )


def build_upload_outcome_row(outcome: UploadOutcome) -> UploadOutcomeRow:
    """Shape one accepted upload."""
    return UploadOutcomeRow(
        file=build_stored_file_row(outcome.record),
        sniff=SniffRow(
            declared_type=outcome.sniff.declared_type,
            sniffed_type=outcome.sniff.sniffed_type,
            agrees=outcome.sniff.agrees,
            note=outcome.sniff.note,
        ),
        detail=(
            f"stored as {outcome.record.file_id} — the id is server-minted entropy, "
            f"your name {outcome.record.display_name!r} travels only as data"
        ),
    )


def build_image_variants_row(variants: ImageVariants) -> ImageVariantsRow:
    """Shape the image round: decoded facts, both variants, sizes for comparison."""
    return ImageVariantsRow(
        file=build_stored_file_row(variants.record),
        sniff=SniffRow(
            declared_type=variants.sniff.declared_type,
            sniffed_type=variants.sniff.sniffed_type,
            agrees=variants.sniff.agrees,
            note=variants.sniff.note,
        ),
        width=variants.width,
        height=variants.height,
        decoded_format=variants.decoded_format,
        thumbnail_data_url=variants.thumbnail_data_url,
        grayscale_data_url=variants.grayscale_data_url,
        thumbnail_bytes=variants.thumbnail_bytes,
        grayscale_bytes=variants.grayscale_bytes,
        detail=(
            f"decoded {variants.width}×{variants.height} {variants.decoded_format} from "
            "the pixels (never from the declared type) — both variants re-encoded as "
            "PNG, so what comes back is pixels this server produced"
        ),
    )


def build_traversal_row(verdict: TraversalVerdict) -> TraversalRow:
    """Shape one hostile name's verdict, with the defense's own words."""
    if verdict.sanitized_name is None:
        outcome = "REJECTED — nothing path-safe survived the allow-list"
    elif not verdict.containment_holds:
        outcome = (
            f"sanitized to {verdict.sanitized_name!r}, but the RAW name escapes a naive "
            "join — only the containment check plus the minted id keep you safe"
        )
    else:
        outcome = f"sanitized to {verdict.sanitized_name!r} — harmless residue"
    return TraversalRow(
        submitted_name=verdict.submitted_name,
        sanitized_name=verdict.sanitized_name,
        accepted=verdict.accepted,
        storage_key=verdict.storage_key,
        naive_join_target=verdict.naive_join_target,
        containment_holds=verdict.containment_holds,
        verdict=outcome,
    )


def build_chunk_plan(chunk_count: int, chunk_bytes: int, pace_ms: int) -> StreamPlan:
    """Validate the knobs and state the plan (FastAPI bounded the query params)."""
    return StreamPlan(
        chunk_count=chunk_count,
        chunk_bytes=chunk_bytes,
        pace_ms=pace_ms,
        total_bytes=chunk_count * (chunk_bytes + 1),  # payload + the newline
        pacing_note=(
            "simulated pacing: the server sleeps between chunks; a slow client "
            "creates the same stalls without any sleep, via the send buffer"
        ),
    )


def render_stream_chunk(plan: StreamPlan, index: int) -> bytes:
    """One chunk's exact bytes: a JSON line padded to the promised size.

    Deterministic and byte-exact by construction — the stream tests pin the
    sequence, and the client's per-chunk timing multiplies the same payload.
    """
    line = StreamChunk(chunk=index, of=plan.chunk_count, bytes=plan.chunk_bytes)
    payload = json.dumps(line.model_dump(by_alias=True), separators=(",", ":"))
    padding = plan.chunk_bytes - len(payload)
    if padding < 0:  # defensive: bounds make this unreachable, padding stays honest
        payload = payload[: plan.chunk_bytes]
        padding = 0
    return f"{payload}{' ' * padding}\n".encode("ascii")


async def paced_chunks(plan: StreamPlan) -> AsyncIterator[bytes]:
    """The StreamingResponse body: each planned chunk, one sleep between them.

    The sleep is BEFORE each chunk except the first, so an interactive
    watcher sees the first byte immediately and then the cadence. The
    generator holds no state beyond the index — cancellation between chunks
    (client disconnect) is clean by construction.
    """
    for index in range(1, plan.chunk_count + 1):
        if index > 1:
            await asyncio.sleep(plan.pace_ms / 1000)
        yield render_stream_chunk(plan, index)
