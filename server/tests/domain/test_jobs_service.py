"""The jobs console service over fakes at the port boundary.

The worker-integration truth lives in the live smoke (a real worker,
real redis, real retries); what is deterministically testable here is
everything the service OWNS: catalog validation at the boundary, the
snapshot's status composition (key layout first, trail splitting the
terminal states, the honest no-trail failure), the dead-letter record
+ replay flow (new job id, attempts reset, audit entry kept), and the
comparison's in-process half and firing choreography.
"""

from typing import Any

import pytest

from guide.core.errors import AppError, FailureKind
from guide.domain.jobs.ports import (
    AttemptOutcome,
    AttemptStepRow,
    ComparisonRunRow,
    DeadLetterRow,
    EmailDraft,
    HeartbeatRow,
    JobLifecycleRow,
    JobTicket,
    MailboxRow,
    QueueStatsRow,
)
from guide.domain.jobs.service import JobsConsoleService, park_dead_letter


class FakeJobsStore:
    """In-memory JobsStore — the port contract, satisfied with lists."""

    def __init__(self) -> None:
        self.lifecycles: dict[str, JobLifecycleRow] = {}
        self.trails: dict[str, list[AttemptStepRow]] = {}
        self.dead_letters: list[DeadLetterRow] = []
        self.mailbox: list[MailboxRow] = []
        self.comparisons: list[ComparisonRunRow] = []
        self.enqueued: list[tuple[str, str | None]] = []
        self.ticket_seq = 0
        self.beats = 0

    async def enqueue(self, function_name: str, payload: str | None) -> JobTicket:
        self.enqueued.append((function_name, payload))
        self.ticket_seq += 1
        return JobTicket(
            job_id=f"job-{self.ticket_seq}",
            function_name=function_name,
            enqueued_at_ms=1_000,
        )

    async def lifecycle(self, job_id: str) -> JobLifecycleRow:
        return self.lifecycles.get(job_id, JobLifecycleRow(state="gone", score_ms=None))

    async def queue_stats(self) -> QueueStatsRow:
        return QueueStatsRow(depth=len(self.enqueued), oldest_age_seconds=None)

    async def note(self, job_id: str, step: AttemptStepRow) -> None:
        self.trails.setdefault(job_id, []).append(step)

    async def steps(self, job_id: str) -> list[AttemptStepRow]:
        return list(self.trails.get(job_id, []))

    async def record_dead_letter(self, entry: DeadLetterRow) -> None:
        self.dead_letters.append(entry)

    async def dead_letters(self, limit: int) -> list[DeadLetterRow]:
        return list(reversed(self.dead_letters))[:limit]

    async def replay_dead_letter(self, entry_id: str) -> JobTicket:
        for index, entry in enumerate(self.dead_letters):
            if entry.entry_id != entry_id:
                continue
            ticket = await self.enqueue(entry.function_name, entry.payload or None)
            self.dead_letters[index] = entry.model_copy(
                update={"replayed_as": ticket.job_id}
            )
            return ticket
        raise AppError(FailureKind.NOT_FOUND, f"dead-letter entry {entry_id!r} is not parked")

    async def dead_letter_size(self) -> int:
        return len(self.dead_letters)

    async def record_message(self, message: MailboxRow) -> None:
        self.mailbox.append(message)

    async def messages(self, limit: int) -> list[MailboxRow]:
        return list(reversed(self.mailbox))[:limit]

    async def mailbox_size(self) -> int:
        return len(self.mailbox)

    async def beat(self) -> int:
        self.beats += 1
        return self.beats

    async def read(self) -> HeartbeatRow:
        return HeartbeatRow(last_run_ms=42_000, beats=self.beats, schedule="test")

    async def record(self, run: ComparisonRunRow) -> None:
        self.comparisons.append(run)

    async def recent(self, limit: int) -> list[ComparisonRunRow]:
        return list(reversed(self.comparisons))[:limit]

    async def reset_demo_state(self) -> int:
        cleared = len(self.trails) + len(self.dead_letters) + len(self.mailbox)
        self.trails.clear()
        self.dead_letters.clear()
        self.mailbox.clear()
        self.comparisons.clear()
        return cleared


def _step(attempt: int, outcome: AttemptOutcome, detail: str = "") -> AttemptStepRow:
    return AttemptStepRow(attempt=attempt, outcome=outcome, detail=detail, at_ms=1)


def _service(store: FakeJobsStore) -> JobsConsoleService:
    return JobsConsoleService(store)  # the fake satisfies the Protocol structurally


class TestEnqueue:
    async def test_unknown_names_fail_at_the_boundary_with_the_catalog(self) -> None:
        with pytest.raises(AppError) as raised:
            await _service(FakeJobsStore()).enqueue("not_a_job")
        assert raised.value.kind.value == "validation_failed"
        assert "fail_once" in raised.value.message

    async def test_known_names_pass_through_to_the_broker(self) -> None:
        store = FakeJobsStore()
        ticket = await _service(store).enqueue("fast")
        assert ticket.function_name == "fast"
        assert store.enqueued == [("fast", None)]

    async def test_email_drafts_travel_as_json_payloads(self) -> None:
        store = FakeJobsStore()
        draft = EmailDraft(to="ada@example.com", subject="hi")
        await _service(store).enqueue_email(draft)
        name, payload = store.enqueued[0]
        assert name == "send_email"
        assert '"to":"ada@example.com"' in payload


class TestSnapshot:
    async def test_live_states_come_from_the_key_layout(self) -> None:
        for state in ("in_progress", "queued", "deferred"):
            store = FakeJobsStore()
            store.lifecycles["j"] = JobLifecycleRow(state=state, score_ms=99)
            snapshot = await _service(store).snapshot("j")
            assert snapshot.status == state

    async def test_the_trails_last_step_splits_the_terminal_states(self) -> None:
        store = FakeJobsStore()
        store.trails["done"] = [_step(1, "succeeded")]
        store.trails["dead"] = [_step(1, "retry_scheduled"), _step(2, "failed_final")]
        service = _service(store)
        assert (await service.snapshot("done")).status == "complete"
        dead = await service.snapshot("dead")
        assert dead.status == "failed"
        assert dead.dead_lettered is True
        assert (await service.snapshot("done")).dead_lettered is False

    async def test_a_retained_result_without_a_trail_is_an_honest_failure(self) -> None:
        store = FakeJobsStore()
        store.lifecycles["j"] = JobLifecycleRow(state="result_present", score_ms=None)
        snapshot = await _service(store).snapshot("j")
        assert snapshot.status == "failed"
        assert "died before its first note" in (snapshot.result or "")

    async def test_nothing_anywhere_is_not_found(self) -> None:
        snapshot = await _service(FakeJobsStore()).snapshot("ghost")
        assert snapshot.status == "not_found"
        assert snapshot.result is None


class TestDeadLetterFlow:
    async def test_parking_records_the_entry_and_the_final_trail_note(self) -> None:
        store = FakeJobsStore()
        entry = await park_dead_letter(
            store,
            job_id="j1",
            function_name="fail_always",
            attempts=3,
            reason="budget spent",
            payload="",
            failed_at_ms=5_000,
        )
        assert entry.job_id == "j1" and entry.attempts == 3
        assert store.dead_letters == [entry]
        last = store.trails["j1"][-1]
        assert last.outcome == "failed_final"
        assert "budget spent" in last.detail

    async def test_replay_re_enqueues_fresh_and_keeps_the_audit_entry(self) -> None:
        store = FakeJobsStore()
        await store.record_dead_letter(
            DeadLetterRow(
                entry_id="e1",
                job_id="j1",
                function_name="fail_always",
                attempts=3,
                reason="budget spent",
                failed_at_ms=5_000,
                payload="",
            )
        )
        ticket = await _service(store).replay("e1")
        assert ticket.job_id != "j1", "replay mints a NEW job id"
        assert ticket.function_name == "fail_always"
        kept = store.dead_letters[0]
        assert kept.job_id == "j1", "the audit entry stays"
        assert kept.replayed_as == ticket.job_id, "and links to its replacement"
        assert ("fail_always", None) in store.enqueued, "empty payload re-enqueues arg-less"


class TestTheComparison:
    async def test_fire_schedules_in_process_and_enqueues_queued(self) -> None:
        store = FakeJobsStore()
        scheduled: list[tuple[Any, ...]] = []

        def scheduler(*args: Any) -> None:
            scheduled.append(args)

        run_id, ticket = await _service(store).fire_comparison(scheduler)
        assert run_id and ticket.function_name == "comparison_work"
        assert len(scheduled) == 1, "the in-process half is scheduled, not run"
        name, payload = store.enqueued[0]
        assert name == "comparison_work"
        assert f'"runId": "{run_id}"' in payload, "the decision instant travels in the payload"

    async def test_the_in_process_half_files_its_row(self) -> None:
        store = FakeJobsStore()
        service = _service(store)
        await service.run_in_process_comparison("run-1", decided_at_ms=1_000)
        row = store.comparisons[0]
        assert row.side == "in_process"
        assert row.run_id == "run-1"
        assert row.handoff_duration_ms >= 0
        assert row.work_duration_ms >= 0
