"""Image work with Pillow: decode honestly, derive variants deterministically.

The upload pipeline's sniffing (``validation.py``) answers "is this really a
PNG/JPEG?" from magic bytes; this module answers the NEXT question — "can it
actually be decoded as one?" — because a body can carry a PNG signature in
front of truncated pixel data: magic bytes agree, decoding fails. The
failure is mapped to the standard ``validation_failed`` 422 envelope
(Pillow's decode errors are ``UnidentifiedImageError``/``OSError``/
``ValueError`` under the hood), so a hostile or broken image can never
produce a 500 out of the image endpoint.

Two variants are derived, both re-encoded as PNG so results are lossless,
byte-deterministic for identical input (pinned by test), and safe to serve
(the re-encode strips any EXIF/ICC weirdness and any polyglot payload the
original carried — the output is pixels Pillow produced, not bytes the
uploader chose):

- ``make_thumbnail`` — the classic upload-side op: fit within a max edge,
  preserving aspect ratio (Pillow's in-place ``thumbnail``), used for
  previews, avatars, gallery grids.
- ``make_grayscale`` — the same pixels, one channel: the cheapest real
  transform that proves the pipeline is doing IMAGE math, not file
  shuffling.

``inspect_image`` is the shared gate: dimensions and format come from the
DECODED image (never from the declared content type), and every other op
runs through it first — one place decides what "decodable" means.
"""

import base64
import io
from dataclasses import dataclass
from typing import Final

from PIL import Image, UnidentifiedImageError

from guide.core.errors import AppError, FailureKind

THUMBNAIL_MAX_EDGE: Final[int] = 96
"""Thumbnails fit inside a 96×96 box, aspect ratio preserved."""

VARIANT_FORMAT: Final[str] = "PNG"
"""Derived variants re-encode as PNG — lossless, deterministic, payload-free."""


@dataclass(frozen=True, slots=True)
class ImageFacts:
    """What decoding proved: dimensions and the real format, from the pixels."""

    width: int
    height: int
    format: str


def _open(body: bytes) -> Image.Image:
    """Decode the body fully (truncated data fails HERE, not mid-transform)."""
    try:
        image = Image.open(io.BytesIO(body))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise AppError(
            FailureKind.VALIDATION_FAILED,
            f"upload rejected — the body is not a decodable image ({type(error).__name__})",
            details={
                "why": "magic bytes matched, but full decoding failed — likely truncated "
                "or corrupted pixel data",
            },
        ) from error
    return image


def inspect_image(body: bytes) -> ImageFacts:
    """Decode and report the truth: dimensions + format, from the image itself."""
    with _open(body) as image:
        return ImageFacts(width=image.width, height=image.height, format=image.format or "?")


def make_thumbnail(body: bytes, max_edge: int = THUMBNAIL_MAX_EDGE) -> bytes:
    """Fit the image inside a ``max_edge`` box (aspect preserved), re-encoded PNG."""
    with _open(body) as image:
        image.thumbnail(size=(max_edge, max_edge))
        buffer = io.BytesIO()
        image.save(buffer, format=VARIANT_FORMAT)
        return buffer.getvalue()


def make_grayscale(body: bytes) -> bytes:
    """The same image in one luminance channel, re-encoded PNG, dimensions kept."""
    with _open(body) as image:
        grayscale = image.convert("L")
        buffer = io.BytesIO()
        grayscale.save(buffer, format=VARIANT_FORMAT)
        return buffer.getvalue()


def encode_data_url(body: bytes) -> str:
    """Wrap variant bytes as a data URL the workbench can render directly."""
    base64_data = base64.b64encode(body).decode("ascii")
    return f"data:image/png;base64,{base64_data}"
