"""Upload validation: content sniffing and the size cap, both before trust.

Two questions every upload endpoint must answer BEFORE the bytes become a
stored file: is this body actually the type it claims, and is it small
enough to accept at all? Both are enforced here, in the domain, so the
router stays a parser/mapper and every rejection is the ONE taxonomy's
``validation_failed`` 422 envelope (``AppError`` — the same mechanism the
auth services use).

SNIFFING — the declared ``Content-Type`` of a multipart part is CLIENT
ASSERTION, not fact: the browser sends the file's MIME from the sending
OS's table, and a script can send any string it likes. The magic-bytes
table below reads the first bytes of the BODY and names what the bytes
actually are; ``validate_content_agreement`` requires claim and bytes to
agree, with one honest escape hatch — ``application/octet-stream`` is the
"no claim" content type, and an unclaimed body is accepted with the sniff
recorded (the workbench shows the verdict either way). A ``.jpg``
extension with PNG bytes is the classic mismatch this catches: serving
that file later as ``image/jpeg`` would make the browser mis-render it
at best and execute a polyglot at worst.

THE CAP — ``MAX_UPLOAD_BYTES`` (2 MiB) is the demo-scoped instance of the
production rule: an upload endpoint without a cap is a memory-DoS
invitation, because SOMEWHERE the body gets buffered and "somewhere" is
usually RAM. The cap is enforced by the CALLER reading at most
``MAX_UPLOAD_BYTES + 1`` bytes from the stream and handing the result to
``validate_size`` — one byte over the cap is proof the body is larger,
without ever holding the whole thing (the streamed read is the §1 lesson;
this module only judges its result).
"""

from dataclasses import dataclass
from typing import Final

from guide.core.errors import AppError, FailureKind

MAX_UPLOAD_BYTES: Final[int] = 2 * 1024 * 1024
"""The workbench's upload cap: 2 MiB — demo-scoped, but the shape is the rule."""

MAGIC_SIGNATURES: Final[tuple[tuple[bytes, str], ...]] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
)
"""Leading magic bytes → the type the BODY declares, longest-first callers beware:
signatures are ordered so overlapping prefixes (GIF87a/GIF89a) both match."""

TEXT_CONTENT_TYPE: Final[str] = "text/plain"
GENERIC_CONTENT_TYPE: Final[str] = "application/octet-stream"
"""What a sniff that matches NO signature reports, and the one declared type
that makes no claim to check agreement against."""


@dataclass(frozen=True, slots=True)
class SniffVerdict:
    """What the bytes say: the sniffed type, and whether the claim agreed."""

    declared_type: str
    sniffed_type: str
    agrees: bool
    note: str


def sniff_content_type(body: bytes) -> str:
    """Name the body by its leading magic bytes; unclaimed bodies are octet-stream.

    Text gets a pragmatic sniff: no magic bytes exist for it, but a body
    that decodes cleanly as UTF-8 and holds no NUL byte is text-shaped —
    good enough to CATCH a binary masquerading as ``text/plain``, which is
    the direction that matters (the reverse mismatch is caught by the
    signature table).
    """
    for signature, content_type in MAGIC_SIGNATURES:
        if body.startswith(signature):
            return content_type
    if b"\x00" not in body[:512]:
        try:
            body[:512].decode("utf-8")
        except UnicodeDecodeError:
            return GENERIC_CONTENT_TYPE
        return TEXT_CONTENT_TYPE
    return GENERIC_CONTENT_TYPE


def validate_size(body: bytes) -> None:
    """Reject an over-cap body with the standard 422 envelope.

    The caller has already read at most ``MAX_UPLOAD_BYTES + 1`` bytes from
    the stream; arriving here with more than the cap means the FULL body is
    strictly larger — proof obtained without holding it.
    """
    if len(body) > MAX_UPLOAD_BYTES:
        raise AppError(
            FailureKind.VALIDATION_FAILED,
            (
                f"upload rejected — body exceeds the {MAX_UPLOAD_BYTES}-byte cap "
                f"(at least {len(body)} bytes)"
            ),
            details={
                "maxUploadBytes": MAX_UPLOAD_BYTES,
                "observedBytes": len(body),
                "divergence": (
                    "HTTP would name this 413 Payload Too Large; this guide maps "
                    "every input rejection onto its one validation_failed envelope "
                    "(422) — taught in the topic's range section"
                ),
            },
        )


def validate_content_agreement(declared_type: str, body: bytes) -> SniffVerdict:
    """Require the declared content type to agree with what the bytes say.

    ``application/octet-stream`` declares nothing, so it always agrees (the
    sniff still rides the verdict — the workbench shows it). Any other
    declared type must equal the sniffed one, else the 422 envelope names
    both sides of the disagreement.
    """
    sniffed = sniff_content_type(body)
    if declared_type == GENERIC_CONTENT_TYPE:
        return SniffVerdict(
            declared_type=declared_type,
            sniffed_type=sniffed,
            agrees=True,
            note="no claim was made (octet-stream) — the sniff is recorded, not checked",
        )
    agrees = declared_type == sniffed
    if not agrees:
        raise AppError(
            FailureKind.VALIDATION_FAILED,
            (
                "upload rejected — declared content type "
                f"{declared_type!r} disagrees with the body's magic bytes "
                f"({sniffed!r})"
            ),
            details={
                "declaredType": declared_type,
                "sniffedType": sniffed,
                "why": "the declared type is client assertion; magic bytes are fact",
            },
        )
    return SniffVerdict(
        declared_type=declared_type,
        sniffed_type=sniffed,
        agrees=True,
        note="declared type matches the magic bytes",
    )
