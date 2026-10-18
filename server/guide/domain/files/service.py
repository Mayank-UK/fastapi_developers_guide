"""The files workbench service: the upload/download pipeline in one place.

Everything the demo routers call, in the domain, so the routers stay thin
(the family invariant): an ``upload`` that reads a body STREAM with the cap
enforced while reading (never holding more than cap + one chunk), sniffs
the magic bytes against the declared type, mints a server-side id, and
stores the snapshot; a ``download`` pair (full and ranged) built on the
RFC 9110 range engine; an ``image_variants`` op that uploads AND derives
thumbnail + grayscale; and the ``traversal_verdict`` that shows the naming
defense deciding on a hostile name.

Every rejection — over-cap, MIME disagreement, undecodable image, invalid
or unsatisfiable range, unknown id where 404 is right — rides the ONE
error taxonomy (``AppError`` → envelope), which is the topic's standing
lesson: these are input rejections, and this guide's input rejections are
``validation_failed`` 422s (the deliberate 413/416 divergence, taught in
prose beside the code).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final

from guide.core.errors import AppError, FailureKind
from guide.domain.files.disposition import clean_display_name
from guide.domain.files.images import (
    encode_data_url,
    inspect_image,
    make_grayscale,
    make_thumbnail,
)
from guide.domain.files.naming import safe_join, sanitize_filename
from guide.domain.files.ranges import (
    RANGE_UNIT,
    ResolvedRange,
    parse_range_header,
    resolve_range,
)
from guide.domain.files.storage import FileStore, StoredFile
from guide.domain.files.validation import (
    MAX_UPLOAD_BYTES,
    SniffVerdict,
    validate_content_agreement,
    validate_size,
)

READ_CHUNK_BYTES: Final[int] = 64 * 1024
"""Streamed-read granularity: small enough to bound memory, large enough to matter."""

ByteReader = Callable[[int], Awaitable[bytes]]
"""An async ``read(n)`` — exactly Starlette's ``UploadFile.read`` shape."""

ILLUSTRATIVE_ROOT: Final[str] = "/srv/uploads"
"""The virtual root the traversal verdict illustrates containment against."""


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    """A stored upload plus the sniff verdict that admitted it."""

    record: StoredFile
    sniff: SniffVerdict


@dataclass(frozen=True, slots=True)
class ImageVariants:
    """An uploaded image's derived facts and variants, as servable data URLs."""

    record: StoredFile
    sniff: SniffVerdict
    width: int
    height: int
    decoded_format: str
    thumbnail_data_url: str
    grayscale_data_url: str
    thumbnail_bytes: int
    grayscale_bytes: int


@dataclass(frozen=True, slots=True)
class TraversalVerdict:
    """What the naming defense does with one hostile name, shown not told."""

    submitted_name: str
    sanitized_name: str | None
    accepted: bool
    storage_key: str
    naive_join_target: str
    containment_holds: bool


class FilesWorkbenchService:
    """Upload → validate → store → download over the ``FileStore`` port."""

    def __init__(self, store: FileStore) -> None:
        """Hold the store; every method is stateless bookkeeping over it."""
        self._store = store

    @property
    def store(self) -> FileStore:
        """The store the composition root wired (the workbench lists through it)."""
        return self._store

    async def upload(
        self, display_name: str, declared_type: str, read: ByteReader
    ) -> UploadOutcome:
        """Read the body STREAM under the cap, sniff it, store it.

        The read loop is the cap's enforcement point: it accumulates at most
        ``MAX_UPLOAD_BYTES + READ_CHUNK_BYTES`` bytes — one chunk over the cap
        is proof of oversize, obtained without ever holding the full body
        (the §1 lesson: the body is a stream, and a cap you check after
        reading everything is not a cap).
        """
        body = bytearray()
        while True:
            chunk = await read(READ_CHUNK_BYTES)
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_UPLOAD_BYTES:
                # Proof of oversize, obtained without the rest of the body.
                validate_size(bytes(body))
        return self._store_upload(display_name, declared_type, bytes(body))

    def _store_upload(self, display_name: str, declared_type: str, body: bytes) -> UploadOutcome:
        """The synchronous half: sniff agreement, sanitize, store."""
        sniff = validate_content_agreement(declared_type, body)
        sanitized = sanitize_filename(display_name)
        if sanitized is None:
            raise AppError(
                FailureKind.VALIDATION_FAILED,
                (
                    f"upload rejected — filename {display_name!r} has no path-safe "
                    "residue (only [A-Za-z0-9._-] survive sanitizing)"
                ),
                details={
                    "submittedName": display_name,
                    "why": "a name that sanitizes to nothing is rejected, not defaulted",
                },
            )
        record = self._store.save(
            display_name=clean_display_name(display_name),
            sanitized_name=sanitized,
            body=body,
            declared_type=declared_type,
            sniffed_type=sniff.sniffed_type,
        )
        return UploadOutcome(record=record, sniff=sniff)

    async def image_variants(
        self, display_name: str, declared_type: str, read: ByteReader
    ) -> ImageVariants:
        """Upload an image, then derive thumbnail + grayscale from the pixels.

        Runs the SAME upload pipeline first (cap, sniff agreement, sanitized
        store), so an image upload is never a second code path — then decodes
        for real: a body with agreeing magic bytes but truncated pixel data
        dies HERE with the standard 422, not mid-transform with a 500.
        """
        uploaded = await self.upload(display_name, declared_type, read)
        body = self._store.read(uploaded.record.file_id)
        assert body is not None, "the record was just stored under this id"
        facts = inspect_image(body)
        thumbnail = make_thumbnail(body)
        grayscale = make_grayscale(body)
        return ImageVariants(
            record=uploaded.record,
            sniff=uploaded.sniff,
            width=facts.width,
            height=facts.height,
            decoded_format=facts.format,
            thumbnail_data_url=encode_data_url(thumbnail),
            grayscale_data_url=encode_data_url(grayscale),
            thumbnail_bytes=len(thumbnail),
            grayscale_bytes=len(grayscale),
        )

    def download(self, file_id: str) -> tuple[StoredFile, bytes]:
        """The full body plus its metadata; unknown ids are the standard 404."""
        record = self._require(file_id)
        body = self._store.read(file_id)
        assert body is not None, "metadata and bytes are stored together"
        return record, body

    def ranged_download(
        self, file_id: str, range_value: str | None
    ) -> tuple[StoredFile, bytes, ResolvedRange] | None:
        """Resolve a Range header against one stored file.

        Returns None when NO range applies (the caller serves the full 200).
        A syntactically invalid range and an unsatisfiable one are BOTH the
        standard 422 envelope here — the documented divergence from the
        RFC-strict 416, with the RFC's behavior named in the details.
        """
        if range_value is None or not range_value.strip():
            return None
        record, body = self.download(file_id)
        parsed = parse_range_header(range_value)
        if parsed is None:
            raise AppError(
                FailureKind.VALIDATION_FAILED,
                f"invalid Range header {range_value!r} — expected one '{RANGE_UNIT}=a-b' window",
                details={
                    "rangeValue": range_value,
                    "divergence": (
                        "RFC 9110 answers an unsatisfiable range with 416 (and says a "
                        "server MAY ignore an invalid one and serve 200); this guide "
                        "maps both onto validation_failed 422 — one envelope for every "
                        "input rejection"
                    ),
                },
            )
        resolved = resolve_range(parsed, len(body))
        if resolved is None:
            raise AppError(
                FailureKind.VALIDATION_FAILED,
                (
                    f"range not satisfiable — the file holds {len(body)} bytes and the "
                    f"range starts at byte {parsed.first}"
                ),
                details={
                    "rangeValue": range_value,
                    "fileSizeBytes": len(body),
                    "requestedFirstByte": parsed.first,
                    "divergence": "the RFC-strict answer is 416 Range Not Satisfiable",
                },
            )
        return record, body[resolved.start : resolved.end + 1], resolved

    def traversal_verdict(self, submitted_name: str) -> TraversalVerdict:
        """Run one hostile name through the whole naming defense, for show.

        Shows all three layers: what the allow-list sanitizer keeps, where a
        NAIVE join of the raw name would land (escape), and whether
        resolve-then-contain accepts it. The storage key column is the
        punchline — it is server-minted entropy, so it never needed the
        name in the first place.
        """
        sanitized = sanitize_filename(submitted_name)
        naive_target = f"{ILLUSTRATIVE_ROOT}/{submitted_name}"
        containment_holds = safe_join(ILLUSTRATIVE_ROOT, submitted_name) is not None
        accepted = sanitized is not None and containment_holds
        return TraversalVerdict(
            submitted_name=submitted_name,
            sanitized_name=sanitized,
            accepted=accepted,
            storage_key="f-<server-minted hex — never derived from the name>",
            naive_join_target=naive_target,
            containment_holds=containment_holds,
        )

    def _require(self, file_id: str) -> StoredFile:
        """Fetch metadata or raise the standard 404 (existence is a domain answer)."""
        record = self._store.find(file_id)
        if record is None:
            raise AppError(FailureKind.NOT_FOUND, f"stored file {file_id!r} not found")
        return record
