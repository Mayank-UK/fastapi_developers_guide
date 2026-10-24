"""The patterns substrate's engines: the saga coordinator + the event store.

Unit tests with integer inputs only (the breaker's discipline): the
saga's compensation order is REVERSED over completed steps and its
ledger evidence is per-step; the event store's versions are dense, its
optimistic-concurrency refusals append NOTHING, and the pure fold
rebuilds identical state from identical history — the property all of
event sourcing stands on. The demo endpoint tests (tests/demo/) pin
the wire; these pin the engines underneath.
"""

from typing import Final

import pytest

from guide.data.patterns.memory_event_store import InMemoryEventStore
from guide.domain.patterns.event_store import (
    EXPECT_EMPTY,
    EventDraft,
    UnknownEventTypeError,
    VersionConflict,
    fold_stream,
)
from guide.domain.patterns.saga import (
    DEMO_ORDER_SAGA,
    SagaCoordinator,
    SagaDefinition,
    SagaStep,
    SagaStepFailure,
)


class TestSagaCoordinator:
    """run(): forward order, reverse compensation, honest failure records."""

    def test_a_happy_run_commits_every_step_in_order(self) -> None:
        coordinator = SagaCoordinator(clock=lambda: 0.0)
        effects = {step.action: _sayer(f"{step.action} done") for step in DEMO_ORDER_SAGA.steps}
        outcome = coordinator.run(DEMO_ORDER_SAGA, effects)
        assert outcome.outcome == "committed"
        assert outcome.failure_step is None
        assert outcome.compensation_order == ()
        assert [entry.step for entry in outcome.entries] == [
            "reserve-item",
            "charge-card",
            "book-shipment",
            "announce-order",
        ]
        assert all(
            entry.phase == "forward" and entry.outcome == "done" for entry in outcome.entries
        )

    def test_a_failing_step_runs_compensations_in_reverse_order(self) -> None:
        coordinator = SagaCoordinator(clock=lambda: 0.0)
        effects = {
            "reserve-item": _sayer("stock widgets 2 -> 1"),
            "release-item": _sayer("stock widgets 1 -> 2"),
            "charge-card": _sayer("balance 0 -> 4900 cents"),
            "refund-card": _sayer("balance 4900 -> 0 cents"),
            "book-shipment": _raiser("carrier full"),
            "cancel-shipment": _sayer("slot released"),
            "announce-order": _sayer("announced"),
            "retract-announce": _sayer("retracted"),
        }
        outcome = coordinator.run(DEMO_ORDER_SAGA, effects)
        assert outcome.outcome == "compensated"
        assert outcome.failure_step == "book-shipment"
        # THE proof: undo ran over the two completed steps, newest-first.
        assert outcome.compensation_order == ("refund-card", "release-item")
        assert [entry.step for entry in outcome.entries] == [
            "reserve-item",
            "charge-card",
            "book-shipment",
            "refund-card",
            "release-item",
        ]
        phases = [entry.phase for entry in outcome.entries]
        assert phases == ["forward", "forward", "forward", "compensate", "compensate"]
        # The failed step carries its evidence; the never-reached step left no trace.
        failed = outcome.entries[2]
        assert failed.outcome == "failed"
        assert "carrier full" in failed.evidence
        assert "announce-order" not in [entry.step for entry in outcome.entries]
        # Per-step evidence survives: every entry carries its own line.
        assert outcome.entries[0].evidence == "stock widgets 2 -> 1"
        assert outcome.entries[3].evidence == "balance 4900 -> 0 cents"

    def test_a_failure_on_the_first_step_has_nothing_to_undo(self) -> None:
        coordinator = SagaCoordinator(clock=lambda: 0.0)
        effects = {"reserve-item": _raiser("out of stock")}
        outcome = coordinator.run(DEMO_ORDER_SAGA, effects)
        assert outcome.outcome == "compensated"
        assert outcome.compensation_order == ()
        assert len(outcome.entries) == 1
        assert outcome.entries[0].outcome == "failed"

    def test_an_unexpected_exception_fails_the_step_and_is_recorded(self) -> None:
        definition = SagaDefinition(
            name="tiny",
            steps=(SagaStep(action="a", compensates="undo-a", describes="first"),),
        )

        def boom() -> str:
            raise RuntimeError("socket exploded")

        outcome = SagaCoordinator(clock=lambda: 0.0).run(definition, {"a": boom})
        assert outcome.outcome == "compensated"
        assert outcome.entries[0].outcome == "failed"
        assert "RuntimeError" in outcome.entries[0].evidence
        assert "socket exploded" in outcome.entries[0].evidence

    def test_a_failing_compensation_is_recorded_and_the_undo_continues(self) -> None:
        definition = SagaDefinition(
            name="three-step",
            steps=(
                SagaStep(action="a", compensates="undo-a", describes="first"),
                SagaStep(action="b", compensates="undo-b", describes="second"),
                SagaStep(action="c", compensates="undo-c", describes="third"),
            ),
        )
        effects = {
            "a": lambda: "a done",
            "undo-a": lambda: "a undone",
            "b": lambda: "b done",
            "undo-b": _raiser("refund api down"),
            "c": _raiser("late failure"),
            "undo-c": lambda: "c undone",
        }
        outcome = SagaCoordinator(clock=lambda: 0.0).run(definition, effects)
        assert outcome.outcome == "compensated"
        # undo-b refused; undo-a still ran — older work is never left undone.
        assert outcome.compensation_order == ("undo-b", "undo-a")
        by_step = {entry.step: entry for entry in outcome.entries}
        assert by_step["undo-b"].outcome == "compensation-failed"
        assert "refund api down" in by_step["undo-b"].evidence
        assert by_step["undo-a"].outcome == "compensated"

    def test_the_clock_is_read_once_per_log_entry(self) -> None:
        counter = _CounterClock()
        definition = SagaDefinition(
            name="one-step",
            steps=(SagaStep(action="a", compensates="undo-a", describes="only"),),
        )
        outcome = SagaCoordinator(clock=counter).run(definition, {"a": lambda: "done"})
        assert outcome.entries[0].at == 1
        failed = SagaCoordinator(clock=_CounterClock()).run(
            definition, {"a": _raiser("no")}
        )
        assert failed.entries[0].at == 1


class _CounterClock:
    """Integer clock: 1, 2, 3… — sequence proofs are integer math."""

    def __init__(self) -> None:
        self._now = 0

    def __call__(self) -> float:
        self._now += 1
        return float(self._now)


def _raiser(message: str):
    """An effect that fails its step with ``message`` via SagaStepFailure."""

    def fail() -> str:
        raise SagaStepFailure(message)

    return fail


def _sayer(line: str):
    """An effect that succeeds, returning ``line`` as its evidence."""

    def say() -> str:
        return line

    return say


class TestInMemoryEventStore:
    """The adapter: dense versions, total conflicts, ordered reads."""

    def test_versions_are_dense_per_stream_and_the_clock_stamps_each(self) -> None:
        stamps = iter(f"t{n}" for n in range(1, 6))
        store = InMemoryEventStore(clock=lambda: next(stamps))
        stored = store.append(
            "post:alpha",
            [EventDraft("PostCreated", {"title": "A"}), EventDraft("TagAdded", {"tag": "x"})],
            EXPECT_EMPTY,
        )
        assert [event.version for event in stored] == [1, 2]
        assert [event.occurred_at for event in stored] == ["t1", "t2"]
        more = store.append("post:alpha", [EventDraft("PostPublished")], 2)
        assert more[0].version == 3
        assert [event.version for event in store.stream("post:alpha")] == [1, 2, 3]

    def test_two_streams_version_independently(self) -> None:
        store = InMemoryEventStore(clock=lambda: "t")
        store.append("post:a", [EventDraft("PostCreated")], EXPECT_EMPTY)
        store.append("post:b", [EventDraft("PostCreated"), EventDraft("PostEdited")], EXPECT_EMPTY)
        assert [event.version for event in store.stream("post:b")] == [1, 2]
        assert len(store.log()) == 3

    def test_a_stale_expected_version_conflicts_and_appends_nothing(self) -> None:
        store = InMemoryEventStore(clock=lambda: "t")
        store.append(
            "post:a", [EventDraft("PostCreated"), EventDraft("TagAdded")], EXPECT_EMPTY
        )
        with pytest.raises(VersionConflict) as conflict:
            store.append("post:a", [EventDraft("PostEdited")], 1)
        assert conflict.value.stream == "post:a"
        assert conflict.value.expected == 1
        assert conflict.value.actual == 2
        assert "re-fold, retry" in str(conflict.value)
        # Totality: the losing write stored NOTHING — not half a batch.
        assert len(store.stream("post:a")) == 2
        assert len(store.log()) == 2

    def test_writing_a_new_stream_with_a_nonempty_expectation_conflicts(self) -> None:
        store = InMemoryEventStore(clock=lambda: "t")
        with pytest.raises(VersionConflict):
            store.append("post:ghost", [EventDraft("PostCreated")], 4)
        assert store.stream("post:ghost") == []
        assert store.log() == []

    def test_an_unknown_stream_reads_empty_and_ids_are_minted(self) -> None:
        store = InMemoryEventStore(clock=lambda: "t")
        assert store.stream("nope") == []
        stored = store.append("post:a", [EventDraft("PostCreated")], EXPECT_EMPTY)
        assert stored[0].event_id
        assert len(stored[0].event_id) == 32  # uuid4 hex


class TestFoldStream:
    """The pure fold: same history in, same state out — or a loud error."""

    HANDLERS: Final = {
        "PostCreated": lambda state, event: {
            **state,
            "title": event.payload["title"],
            "tags": [],
        },
        "TagAdded": lambda state, event: {
            **state,
            "tags": [*state["tags"], event.payload["tag"]],
        },
        "PostPublished": lambda state, event: {**state, "status": "published"},
    }

    def test_folding_rebuilds_state_from_the_whole_history(self) -> None:
        store = InMemoryEventStore(clock=lambda: "t")
        store.append(
            "post:a",
            [
                EventDraft("PostCreated", {"title": "First"}),
                EventDraft("TagAdded", {"tag": "arch"}),
                EventDraft("TagAdded", {"tag": "sagas"}),
                EventDraft("PostPublished"),
            ],
            EXPECT_EMPTY,
        )
        state = fold_stream(store.stream("post:a"), {}, self.HANDLERS)
        assert state == {"title": "First", "tags": ["arch", "sagas"], "status": "published"}

    def test_the_same_history_folds_identically_in_a_second_store(self) -> None:
        drafts = [
            EventDraft("PostCreated", {"title": "Rebuild"}),
            EventDraft("TagAdded", {"tag": "event-sourcing"}),
        ]
        first, second = InMemoryEventStore(clock=lambda: "t"), InMemoryEventStore(clock=lambda: "t")
        for store in (first, second):
            store.append("post:a", drafts, EXPECT_EMPTY)
        assert fold_stream(first.stream("post:a"), {}, self.HANDLERS) == fold_stream(
            second.stream("post:a"), {}, self.HANDLERS
        )

    def test_order_matters_the_fold_is_positional_not_temporal(self) -> None:
        one = InMemoryEventStore(clock=lambda: "t")
        two = InMemoryEventStore(clock=lambda: "t")
        one.append(
            "post:a",
            [EventDraft("TagAdded", {"tag": "x"}), EventDraft("PostCreated", {"title": "T"})],
            EXPECT_EMPTY,
        )
        two.append(
            "post:a",
            [EventDraft("PostCreated", {"title": "T"}), EventDraft("TagAdded", {"tag": "x"})],
            EXPECT_EMPTY,
        )
        with pytest.raises(KeyError):
            # TagAdded BEFORE PostCreated touches state the create has not built.
            fold_stream(one.stream("post:a"), {}, self.HANDLERS)
        assert fold_stream(two.stream("post:a"), {}, self.HANDLERS)["tags"] == ["x"]

    def test_an_unhandled_event_type_raises_instead_of_skipping(self) -> None:
        store = InMemoryEventStore(clock=lambda: "t")
        store.append("post:a", [EventDraft("MysteryHappened")], EXPECT_EMPTY)
        with pytest.raises(UnknownEventTypeError) as error:
            fold_stream(store.stream("post:a"), {}, self.HANDLERS)
        assert "MysteryHappened" in str(error.value)

    def test_the_empty_history_folds_to_the_initial_state(self) -> None:
        assert fold_stream([], {"status": "draft"}, self.HANDLERS) == {"status": "draft"}
