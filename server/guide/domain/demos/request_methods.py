"""Request-methods demo substrate: a typed in-memory notes resource.

``/api/demo/reqres/notes`` serves this playground. The demo's point is the
request→response CONTRACT per method, so the substrate keeps each rule
visible: POST validates the body through ``NoteCreate`` (topic 05's
pipeline applied to a request body) and the router answers 201 with a
Location header; GET serves ``NotePublic`` — the stored record carries a
``revision`` counter the response model deliberately filters off the wire,
which is the response_model-as-output-filter lesson in one field; PUT is a
full replace (title/body/tags all arrive; the server keeps identity
metadata — id and created_at — and bumps revision); DELETE answers 204
with no body, and the next GET for that id is the honest 404 envelope. An
invalid POST body is FastAPI's own 422 — the validation_failed envelope
with normalized {loc, msg, type} triples, triggerable on purpose.

``NoteStore`` follows the ScenarioStore pattern (per-app instance wired on
``app.state`` in the composition root): a plain in-memory dict keyed by
int id, seeded so the playground is interesting before the first POST.
Records are frozen snapshots — replace builds a NEW record, never mutates
one in place — and ids only count upward, never reused.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated, Final

from pydantic import Field

from guide.core.serialization import CamelModel


class NoteCreate(CamelModel):
    """The POST/PUT body: the full representation a client sends."""

    title: Annotated[str, Field(min_length=1, max_length=80)]
    body: str = ""
    tags: list[str] = []


class NoteRecord(CamelModel):
    """What the store holds: the public fields plus internal bookkeeping."""

    id: int
    title: str
    body: str
    tags: list[str]
    created_at: str
    revision: int


class NotePublic(CamelModel):
    """The response model: exactly the fields the wire may carry.

    ``revision`` is deliberately absent — the stored record keeps it, the
    response model filters it, and no client ever sees it.
    """

    id: int
    title: str
    body: str
    tags: list[str]
    created_at: str


class NotesListing(CamelModel):
    """Wire shape of GET /api/demo/reqres/notes."""

    count: int
    notes: list[NotePublic]
    reasoning: str


SEED_NOTES: Final[tuple[NoteCreate, ...]] = (
    NoteCreate(
        title="Read the request first",
        body="The handler's view arrives parsed: line, query, headers.",
        tags=["request", "reading"],
    ),
    NoteCreate(
        title="Let pydantic own the body",
        body="A typed model at the boundary validates before code runs.",
        tags=["pydantic", "validation"],
    ),
    NoteCreate(
        title="Filter the way out",
        body="response_model shapes the answer; revision stays inside.",
        tags=["response", "filtering"],
    ),
)


def build_notes_listing(records: Sequence[NoteRecord]) -> NotesListing:
    """Shape the listing payload from stored records (pure)."""
    notes = [
        NotePublic(
            id=record.id,
            title=record.title,
            body=record.body,
            tags=list(record.tags),
            created_at=record.created_at,
        )
        for record in records
    ]
    return NotesListing(
        count=len(notes),
        notes=notes,
        reasoning=(
            f"GET answered 200 with all {len(notes)} notes filtered through "
            "NotePublic: every stored record also carries a revision counter "
            "the response model drops, so the wire shows exactly the five "
            "public fields and never the bookkeeping. The notes live in this "
            "app's in-memory store (fresh per process), so a restart reseeds "
            "them — no persistence layer, by design."
        ),
    )


class NoteStore:
    """In-memory notes: seeded, per-app, deliberately unpersisted."""

    def __init__(self, seed: bool = True) -> None:
        """Start empty or with the fixed seed; ids count from 1."""
        self._notes: dict[int, NoteRecord] = {}
        self._next_id = 1
        if seed:
            for draft in SEED_NOTES:
                self.create(draft)

    def create(self, draft: NoteCreate) -> NoteRecord:
        """Mint a new note; revision starts at 1, created_at is minted now."""
        note = NoteRecord(
            id=self._next_id,
            title=draft.title,
            body=draft.body,
            tags=list(draft.tags),
            created_at=datetime.now(UTC).isoformat(timespec="milliseconds"),
            revision=1,
        )
        self._notes[note.id] = note
        self._next_id += 1
        return note

    def get(self, note_id: int) -> NoteRecord | None:
        """One note, or None when the id is unknown."""
        return self._notes.get(note_id)

    def replace(self, note_id: int, draft: NoteCreate) -> NoteRecord | None:
        """Full-replace the content; keep identity metadata; bump revision.

        Returns None when the id is unknown — the router decides that means
        404, exactly like the registry's topic lookup (topic 01's None
        discipline). The caller's record stays untouched: a NEW frozen
        snapshot replaces the old one in the store.
        """
        current = self._notes.get(note_id)
        if current is None:
            return None
        replaced = NoteRecord(
            id=current.id,
            title=draft.title,
            body=draft.body,
            tags=list(draft.tags),
            created_at=current.created_at,
            revision=current.revision + 1,
        )
        self._notes[note_id] = replaced
        return replaced

    def delete(self, note_id: int) -> bool:
        """Remove one note; False when the id is unknown (second delete)."""
        return self._notes.pop(note_id, None) is not None

    def all(self) -> list[NoteRecord]:
        """Every note in insertion order — a copy, never the live values."""
        return list(self._notes.values())
