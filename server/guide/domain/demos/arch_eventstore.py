"""The event-store demo payload: append, fold, rebuild, conflict — all real.

``GET /api/demo/arch/eventstore`` serves this payload. The panel drives
the REAL ``EventStore`` port through its process-memory adapter: five
facts about one post's lifecycle are appended with dense versions, the
current state is FOLDED from the stream one event at a time (each fold
step is its own evidence row — the state after applying exactly that
fact), a SECOND store instance replays the same drafts and rebuilds
byte-identical state (the replay promise, checked with ``==`` on the
wire), and a stale writer learns the optimistic-concurrency lesson:
its append with ``expected_version`` 3 against a stream at version 5
is refused with ``VersionConflict`` and stores NOTHING.

The contrast row is the topic's argument in miniature: a mutable row
answers "what is the current state?" and keeps only the latest write
(four of the five facts gone); the stream keeps every fact forever and
DERIVES the same answer. The audit-kinship row names the repo's
nearest relative honestly — ``audit_log`` (migration 0001) is
append-only and transactional but is a SIDE-BAND record beside the
mutable rows, while event sourcing makes the log itself the source of
truth. Deterministic throughout: a synthetic clock stamps the events
``t1..t5``, fresh stores per request, no I/O, no sleeps.
"""

from typing import Final, cast

from guide.core.serialization import CamelModel
from guide.data.patterns.memory_event_store import InMemoryEventStore
from guide.domain.patterns.event_store import (
    EXPECT_EMPTY,
    EventDraft,
    EventHandler,
    StoredEvent,
    VersionConflict,
    fold_stream,
)

STREAM: Final = "post:advanced-tour"
"""The one aggregate the demo events describe (streams are per-aggregate)."""

DRAFTS: Final = (
    EventDraft("PostCreated", {"title": "The advanced architecture tour", "author": "ada"}),
    EventDraft("PostEdited", {"title": "The advanced architecture tour, revised"}),
    EventDraft("TagAdded", {"tag": "architecture"}),
    EventDraft("TagAdded", {"tag": "sagas"}),
    EventDraft("PostPublished", {}),
)
"""The five facts, in order — create, edit, two tags, publish."""

STALE_VERSION: Final = 3
"""The rival writer's belief — three versions stale at conflict time."""


class StoreFactsRow(CamelModel):
    """The store's own identity: port, adapter, stream, event count."""

    port: str
    adapter: str
    stream: str
    events: int


class AppendedEventRow(CamelModel):
    """One stored fact: version, type, payload, minted id, clock stamp."""

    version: int
    event_type: str
    payload: str
    event_id: str
    occurred_at: str


class FoldStepRow(CamelModel):
    """Per-event fold evidence: the state after applying exactly this fact."""

    after_version: int
    event_type: str
    state_now: str


class ConcurrencyRow(CamelModel):
    """The optimistic-concurrency proof: the stale write, refused totally."""

    writer: str
    expected_version: int
    actual_version: int
    stored_events_after: int
    evidence: str


class ContrastRow(CamelModel):
    """Mutable row vs event stream: what each keeps, what each answers."""

    approach: str
    keeps: str
    history: str
    answers: str


class KinshipRow(CamelModel):
    """The repo's nearest relative to an event store, honestly placed."""

    relative: str
    where: str
    same: str
    different: str


class ArchEventStorePanel(CamelModel):
    """Wire shape of GET /api/demo/arch/eventstore — the whole tour in one."""

    store: StoreFactsRow
    appended: list[AppendedEventRow]
    fold_steps: list[FoldStepRow]
    current_state: dict[str, object]
    rebuild: dict[str, object]
    concurrency: ConcurrencyRow
    contrast: list[ContrastRow]
    kinship: KinshipRow
    honesty_note: str


def _handlers() -> dict[str, EventHandler]:
    """The five event types' fold rules — each pure: copy-in, next-state-out."""

    def created(state: dict[str, object], event: StoredEvent) -> dict[str, object]:
        return {
            **state,
            "title": event.payload["title"],
            "author": event.payload["author"],
            "tags": [],
            "edits": 0,
            "status": "draft",
        }

    def edited(state: dict[str, object], event: StoredEvent) -> dict[str, object]:
        edits = cast(int, state["edits"]) + 1
        return {**state, "title": event.payload["title"], "edits": edits}

    def tagged(state: dict[str, object], event: StoredEvent) -> dict[str, object]:
        tags = [*cast(list[object], state["tags"]), event.payload["tag"]]
        return {**state, "tags": tags}

    def published(state: dict[str, object], event: StoredEvent) -> dict[str, object]:
        return {**state, "status": "published"}

    return {
        "PostCreated": created,
        "PostEdited": edited,
        "TagAdded": tagged,
        "PostPublished": published,
    }


def _state_line(state: dict[str, object]) -> str:
    """One readable line of a fold state — the per-event evidence text."""
    tag_list = cast(list[object], state["tags"])
    tags = ", ".join(str(tag) for tag in tag_list) or "none"
    return (
        f"title={state['title']!r} status={state['status']} "
        f"tags=[{tags}] edits={state['edits']}"
    )


def build_arch_eventstore_panel() -> ArchEventStorePanel:
    """Drive a fresh store through append → fold → rebuild → conflict.

    Pure with respect to app state: everything below is constructed on
    this call, so the panel is the same on every request (the uuids
    minted per append aside — identity is the store's to mint).
    """
    stamps = iter(f"t{n}" for n in range(1, len(DRAFTS) + 1))
    store = InMemoryEventStore(clock=lambda: next(stamps))
    store.append(STREAM, DRAFTS, EXPECT_EMPTY)
    history = store.stream(STREAM)
    handlers = _handlers()

    fold_steps: list[FoldStepRow] = []
    state: dict[str, object] = {}
    for event in history:
        state = fold_stream([event], state, handlers)
        fold_steps.append(
            FoldStepRow(
                after_version=event.version,
                event_type=event.event_type,
                state_now=_state_line(state),
            )
        )

    replay = InMemoryEventStore(clock=lambda: "replay")
    replay.append(STREAM, DRAFTS, EXPECT_EMPTY)
    replayed_state = fold_stream(replay.stream(STREAM), {}, handlers)
    matches = replayed_state == state

    conflict: VersionConflict | None = None
    try:
        store.append(
            STREAM, [EventDraft("PostEdited", {"title": "stale writer's edit"})], STALE_VERSION
        )
    except VersionConflict as refusal:
        conflict = refusal
    assert conflict is not None, "the stale append must refuse — the demo's contract"
    stored_after_conflict = len(store.log())

    contrast = [
        ContrastRow(
            approach="mutable row (the familiar way)",
            keeps="one row, updated in place — only the latest values",
            history="4 of the 5 facts gone: the create, the first title, the tag order, when",
            answers=(
                "what IS the current state? — instantly, but ask it yesterday's "
                "question and the answer is gone"
            ),
        ),
        ContrastRow(
            approach="event stream (this demo's store)",
            keeps="every fact forever, dense versions, nothing rewritten",
            history="5 of 5 facts retained — the fold replays them in order",
            answers=(
                "what HAPPENED? — and the state is derived, so new questions "
                "(projections) are cheap"
            ),
        ),
    ]

    kinship = KinshipRow(
        relative="audit_log (migration 0001)",
        where="server/alembic/versions/0001_guide_schema.py",
        same=(
            "append-only, identity column, written in the same transaction as the "
            "change it records"
        ),
        different=(
            "a SIDE-BAND record beside mutable rows — event sourcing inverts it: "
            "the log is the source of truth and the current state is derived"
        ),
    )

    return ArchEventStorePanel(
        store=StoreFactsRow(
            port="EventStore", adapter="InMemoryEventStore", stream=STREAM, events=len(history)
        ),
        appended=[
            AppendedEventRow(
                version=event.version,
                event_type=event.event_type,
                payload=str(dict(event.payload)) if event.payload else "{}",
                event_id=event.event_id,
                occurred_at=event.occurred_at,
            )
            for event in history
        ],
        fold_steps=fold_steps,
        current_state=state,
        rebuild={
            "method": (
                "a second InMemoryEventStore instance re-appended the same drafts, "
                "then folded"
            ),
            "state": replayed_state,
            "matches": matches,
            "evidence": (
                f"fold of stream == fold of replay: {matches} — replay determinism is the "
                "property every projection and every rebuild stands on"
            ),
        },
        concurrency=ConcurrencyRow(
            writer="a rival writer holding a three-versions-stale belief",
            expected_version=conflict.expected,
            actual_version=conflict.actual,
            stored_events_after=stored_after_conflict,
            evidence=(
                f"VersionConflict: {conflict} — and the log still holds "
                f"{stored_after_conflict} events: the losing write stored nothing"
            ),
        ),
        contrast=contrast,
        kinship=kinship,
        honesty_note=(
            "Every row came from real calls on this request: the port's adapter "
            "appended five facts, the fold engine derived the state step by step, "
            "a second store instance proved replay determinism, and a stale "
            "append was refused totally by the optimistic-concurrency check. The "
            "adapter is process memory (per request); a production store keeps "
            "the same port over a durable table — the outbox (migration 0004) "
            "is this repo's real durable event-adjacent shape."
        ),
    )
