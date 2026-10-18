"""Request/response demo API: the inspector probe + the methods playground.

Thin routers (family invariant). ``/inspector`` (GET and POST) hands the
pure builder the live ``Request`` object's own facts — request line, query
with every occurrence preserved, selected headers, client address, the
middleware's request id — so the caller watches the server's view change as
the request changes. ``/notes`` is the request→response contract per
method: POST validates a ``NoteCreate`` body and answers 201 + Location
(resolved with ``url_path_for``, never string-pasted); GET serves the
listing or one note through ``NotePublic`` — the stored ``revision`` is
deliberately filtered off the wire; PUT full-replaces (200); DELETE
answers 204 with no body. Unknown ids raise the shared 404 envelope; an
invalid body is FastAPI's own 422 validation_failed envelope.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from guide.core.errors import AppError, FailureKind
from guide.core.request_context import current_request_id
from guide.core.serialization import CamelModel
from guide.domain.demos.request_inspector import (
    RequestInspectorPayload,
    build_request_inspector_payload,
)
from guide.domain.demos.request_methods import (
    NoteCreate,
    NotePublic,
    NoteRecord,
    NotesListing,
    NoteStore,
    build_notes_listing,
)

router = APIRouter(prefix="/api/demo/reqres", tags=["demo:reqres"])


class InspectorBody(CamelModel):
    """Optional POST body: a message the inspector reports as parsed."""

    message: str | None = None


def get_note_store(request: Request) -> NoteStore:
    """FastAPI dependency: the app's notes store (wired in create_app)."""
    store = request.app.state.reqres_notes
    if not isinstance(store, NoteStore):
        raise AppError(FailureKind.INTERNAL, "Notes store not wired on app.state")
    return store


NoteStoreDep = Annotated[NoteStore, Depends(get_note_store)]


def _inspect(request: Request, body_message: str | None) -> RequestInspectorPayload:
    """Collect the live Request's facts once; the pure builder does the rest."""
    client = request.client
    return build_request_inspector_payload(
        method=request.method,
        path=request.url.path,
        raw_query=request.url.query or None,
        query_pairs=request.query_params.multi_items(),
        headers=request.headers,
        client_host=client.host if client is not None else None,
        client_port=client.port if client is not None else None,
        request_id=current_request_id(),
        body_message=body_message,
    )


@router.get(
    "/inspector", response_model=RequestInspectorPayload, response_model_exclude_none=True
)
def read_inspector(request: Request) -> RequestInspectorPayload:
    """Reflect the GET exactly as the Request object reports it."""
    return _inspect(request, None)


@router.post(
    "/inspector", response_model=RequestInspectorPayload, response_model_exclude_none=True
)
def send_inspector(
    request: Request, body: InspectorBody | None = None
) -> RequestInspectorPayload:
    """Reflect the POST — body parsed, content type and length reported."""
    return _inspect(request, body.message if body is not None else None)


@router.get("/notes", response_model=NotesListing)
def list_notes(store: NoteStoreDep) -> NotesListing:
    """Serve the whole collection through the public response model."""
    return build_notes_listing(store.all())


@router.post("/notes", response_model=NotePublic, status_code=201)
def create_note(draft: NoteCreate, response: Response, store: NoteStoreDep) -> NoteRecord:
    """Create from the validated body: 201 + Location names the new resource."""
    note = store.create(draft)
    response.headers["location"] = router.url_path_for("read_note", note_id=note.id)
    return note


@router.get("/notes/{note_id}", response_model=NotePublic)
def read_note(note_id: int, store: NoteStoreDep) -> NoteRecord:
    """Serve one note through NotePublic; unknown ids are the 404 envelope."""
    note = store.get(note_id)
    if note is None:
        raise AppError(FailureKind.NOT_FOUND, f"Note {note_id} not found")
    return note


@router.put("/notes/{note_id}", response_model=NotePublic)
def replace_note(note_id: int, draft: NoteCreate, store: NoteStoreDep) -> NoteRecord:
    """Full-replace the note's content: 200 with the new representation."""
    note = store.replace(note_id, draft)
    if note is None:
        raise AppError(FailureKind.NOT_FOUND, f"Note {note_id} not found")
    return note


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, store: NoteStoreDep) -> Response:
    """Delete the note: 204 No Content, nothing in the body."""
    if not store.delete(note_id):
        raise AppError(FailureKind.NOT_FOUND, f"Note {note_id} not found")
    return Response(status_code=204)
