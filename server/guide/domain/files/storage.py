"""Stored-file metadata and the storage port: what an adapter must do.

``StoredFile`` is the metadata snapshot every files endpoint speaks — the
BYTES travel separately (``FileStore.read``), because a listing should not
carry 2 MiB payloads per row. Note the two names on purpose:

- ``file_id`` is SERVER-MINTED (``f-`` + 8 hex of entropy) and is the only
  thing that ever touches a storage key — an attacker controls none of it.
- ``display_name`` is the user's original name, kept for Content-Disposition
  and listings (encoded at the header boundary, never used for storage),
  beside ``sanitized_name`` — what the traversal-proof allow-list made of
  it — so the workbench can SHOW the difference between the two.

The store is DEMO-SCOPED and honest about it: an in-process dict of bytes.
A restart loses it; a second uvicorn worker cannot see it. Both facts are
taught in the topic and stated on the workbench panel — the PORT is the
seam that makes the honest upgrade (a disk adapter, an S3 adapter) a
composition-root decision instead of a rewrite, exactly like the posts
repository in topic 11.
"""

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Protocol, runtime_checkable

FILE_ID_PREFIX: Final = "f-"
"""Storage ids are visually distinct (``f-ab12cd34``) — they appear in URLs."""

Clock = Callable[[], datetime]
"""Wall clock for stored-at stamps; injected so tests can freeze time."""

default_clock: Final[Clock] = lambda: datetime.now(UTC)  # noqa: E731 — named default


@dataclass(frozen=True, slots=True)
class StoredFile:
    """One stored file's metadata; the bytes live behind ``FileStore.read``."""

    file_id: str
    display_name: str
    sanitized_name: str
    declared_type: str
    sniffed_type: str
    size_bytes: int
    stored_at: datetime


@runtime_checkable
class FileStore(Protocol):
    """The files persistence port: adapters save, find, read, and list."""

    def save(
        self,
        display_name: str,
        sanitized_name: str,
        body: bytes,
        declared_type: str,
        sniffed_type: str,
    ) -> StoredFile:
        """Mint an id, stamp the clock, hold the snapshot + bytes, return metadata."""
        ...

    def find(self, file_id: str) -> StoredFile | None:
        """One file's metadata, or None when the id is unknown."""
        ...

    def read(self, file_id: str) -> bytes | None:
        """One file's bytes, or None when the id is unknown."""
        ...

    def list_files(self) -> list[StoredFile]:
        """Every stored file's metadata, oldest first."""
        ...


class InMemoryFileStore:
    """The demo adapter: bytes in a dict, ids from injected entropy.

    Demo-scoped by declaration — a restart loses everything, and the workbench
    panel says so in plain words. The id and clock factories are injected so
    tests get deterministic ids and timestamps without patching.
    """

    def __init__(
        self,
        id_factory: Callable[[], str] | None = None,
        clock: Clock = default_clock,
    ) -> None:
        """Hold the (empty) store; entropy and clock default to real ones."""
        self._id_factory = id_factory or (lambda: f"{FILE_ID_PREFIX}{secrets.token_hex(4)}")
        self._clock = clock
        self._metadata: dict[str, StoredFile] = {}
        self._bodies: dict[str, bytes] = {}

    def save(
        self,
        display_name: str,
        sanitized_name: str,
        body: bytes,
        declared_type: str,
        sniffed_type: str,
    ) -> StoredFile:
        """Store the snapshot under a fresh server-minted id."""
        record = StoredFile(
            file_id=self._id_factory(),
            display_name=display_name,
            sanitized_name=sanitized_name,
            declared_type=declared_type,
            sniffed_type=sniffed_type,
            size_bytes=len(body),
            stored_at=self._clock(),
        )
        self._metadata[record.file_id] = record
        self._bodies[record.file_id] = body
        return record

    def find(self, file_id: str) -> StoredFile | None:
        """One file's metadata, or None when the id is unknown."""
        return self._metadata.get(file_id)

    def read(self, file_id: str) -> bytes | None:
        """One file's bytes, or None when the id is unknown."""
        return self._bodies.get(file_id)

    def list_files(self) -> list[StoredFile]:
        """Every stored file's metadata, oldest first (insertion order)."""
        return list(self._metadata.values())
