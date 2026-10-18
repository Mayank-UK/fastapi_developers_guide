"""The jobs console service: the use cases over the seven ports.

Thin orchestration with the two decisions the domain actually owns:
enqueue requests are validated against the CATALOG (an unknown name
fails at the boundary with the legal vocabulary in the message), and
the snapshot assembles a job's story from the key layout plus the
attempt trail — status first, the trail's last step splitting terminal
states, dead-letter membership flagged beside it.

The comparison also lives here. One run mints a run id and a decision
instant; both halves then measure the SAME thing — the wall-clock gap
from that instant to the moment the work starts (starlette's
``BackgroundTasks`` after the response flush, arq's worker at queue
pickup) — before running the SAME injected-sleeper workload and filing
their half of the ledger. The scheduling callable arrives as a
parameter (``fire_comparison(schedule_in_process)``), the same
dependency inversion the realtime topic used for ``is_disconnected``,
so the domain never meets a starlette type.

The worker process imports ``park_dead_letter`` — the one piece of DLQ
flow both failure paths share: build the audit row, park it, note the
final attempt on the trail.
"""

import asyncio
import json
import time
import uuid
from collections.abc import Callable
from typing import Final

from guide.core.errors import AppError, FailureKind
from guide.domain.jobs.catalog import JOB_CATALOG, JOB_COMPARISON_WORK, JOB_SEND_EMAIL
from guide.domain.jobs.comparison import IN_PROCESS_HOME, run_comparison_work
from guide.domain.jobs.ports import (
    PANEL_LIMIT,
    AttemptStepRow,
    ComparisonRunRow,
    DeadLetterRow,
    EmailDraft,
    HeartbeatRow,
    JobSnapshotRow,
    JobsStore,
    JobStatusName,
    JobTicket,
    MailboxRow,
    QueueStatsRow,
)

RUN_ID_LENGTH: Final = 8
"""The comparison run id's length — short enough to read, unique enough."""

TaskScheduler = Callable[..., None]
"""``BackgroundTasks.add_task``'s shape — schedule a callable, run it later."""


def _now_ms() -> int:
    """Wall-clock milliseconds — the shared clock both comparison halves use."""
    return int(time.time() * 1000)


async def park_dead_letter(
    store: JobsStore,
    *,
    job_id: str,
    function_name: str,
    attempts: int,
    reason: str,
    payload: str,
    failed_at_ms: int,
) -> DeadLetterRow:
    """The DLQ write both failure paths share: park the audit row, note the trail.

    Called by the worker at the moment the budget is spent (or poison is
    classified) — the LAST thing a dying job does is leave a note a
    human can act on.
    """
    entry = DeadLetterRow(
        entry_id=uuid.uuid4().hex[:RUN_ID_LENGTH],
        job_id=job_id,
        function_name=function_name,
        attempts=attempts,
        reason=reason,
        failed_at_ms=failed_at_ms,
        payload=payload,
    )
    await store.record_dead_letter(entry)
    await store.note(
        job_id,
        AttemptStepRow(
            attempt=attempts,
            outcome="failed_final",
            detail=f"dead-lettered: {reason}",
            at_ms=failed_at_ms,
        ),
    )
    return entry


def _terminal_status(steps: list[AttemptStepRow]) -> JobStatusName | None:
    """The terminal state the trail's last step proves, if there is one."""
    if not steps:
        return None
    return "complete" if steps[-1].outcome == "succeeded" else "failed"


class JobsConsoleService:
    """The console's use cases over the one composed port."""

    def __init__(self, store: JobsStore) -> None:
        self._store = store

    async def enqueue(self, function_name: str, payload: str | None = None) -> JobTicket:
        """Enqueue by catalog name — unknown names fail at the boundary."""
        if function_name not in JOB_CATALOG:
            legal = ", ".join(sorted(JOB_CATALOG))
            raise AppError(
                FailureKind.VALIDATION_FAILED,
                f"unknown job {function_name!r} — the worker registers: {legal}",
            )
        return await self._store.enqueue(function_name, payload)

    async def enqueue_email(self, draft: EmailDraft) -> JobTicket:
        """Compose at the boundary, defer the send: the email-as-job flow."""
        return await self._store.enqueue(JOB_SEND_EMAIL, draft.model_dump_json())

    async def snapshot(self, job_id: str) -> JobSnapshotRow:
        """One job's story: key-layout status, the trail, the verdict."""
        live = await self._store.lifecycle(job_id)
        steps = await self._store.steps(job_id)
        if live.state in ("in_progress", "deferred", "queued"):
            status: JobStatusName = live.state
        elif live.state == "result_present":
            # A retained result with no trail means the task died before its
            # first note (arg mismatch, import failure, a hard kill) — that is
            # a failure, and saying so is the honest default.
            status = _terminal_status(steps) or "failed"
        else:  # gone: only the trail can still remember how it ended
            status = _terminal_status(steps) or "not_found"
        return JobSnapshotRow(
            job_id=job_id,
            status=status,
            attempts=steps,
            result=(
                steps[-1].detail
                if steps
                else (
                    "finished without an attempt trail — the task died before "
                    "its first note (argument mismatch, import failure, or a kill)"
                    if live.state == "result_present"
                    else None
                )
            ),
            dead_lettered=bool(steps) and steps[-1].outcome == "failed_final",
        )

    async def queue_stats(self) -> QueueStatsRow:
        """The two numbers — depth, and how long the oldest job has waited."""
        return await self._store.queue_stats()

    async def dead_letters(self) -> list[DeadLetterRow]:
        """The parked jobs, newest first."""
        return await self._store.dead_letters(PANEL_LIMIT)

    async def replay(self, entry_id: str) -> JobTicket:
        """Re-enqueue a parked job — fresh id, attempts reset, entry kept."""
        return await self._store.replay_dead_letter(entry_id)

    async def mailbox(self) -> list[MailboxRow]:
        """The recorded emails, newest first."""
        return await self._store.messages(PANEL_LIMIT)

    async def heartbeat(self) -> HeartbeatRow:
        """The cron schedule's pulse."""
        return await self._store.read()

    async def comparison_recent(self) -> list[ComparisonRunRow]:
        """The comparison ledger, newest first."""
        return await self._store.recent(PANEL_LIMIT)

    async def run_in_process_comparison(self, run_id: str, decided_at_ms: int) -> None:
        """The in-process half — the callable BackgroundTasks schedules.

        Runs AFTER the response is sent (starlette's guarantee, and its
        limit: the work is alive only as long as the process is), times
        the same injected-sleeper workload the worker runs, and files
        its half of the ledger with the decision-to-start gap.
        """
        work_started = _now_ms()
        work_seconds = await run_comparison_work(asyncio.sleep)
        await self._store.record(
            ComparisonRunRow(
                run_id=run_id,
                side="in_process",
                ran_on=IN_PROCESS_HOME,
                handoff_duration_ms=work_started - decided_at_ms,
                work_duration_ms=work_seconds * 1000,
                finished_at_ms=_now_ms(),
            )
        )

    async def fire_comparison(self, schedule_in_process: TaskScheduler) -> tuple[str, JobTicket]:
        """Fire both halves of one run: schedule in-process, enqueue queued.

        The decision instant is minted ONCE and travels to both halves
        (the queued half inside the job payload), so the ledger's two
        handoff numbers measure the same span against the same clock.
        """
        run_id = uuid.uuid4().hex[:RUN_ID_LENGTH]
        decided_at_ms = _now_ms()
        schedule_in_process(self.run_in_process_comparison, run_id, decided_at_ms)
        payload = json.dumps({"runId": run_id, "decidedAtMs": decided_at_ms})
        ticket = await self._store.enqueue(JOB_COMPARISON_WORK, payload)
        return run_id, ticket

    async def reset(self) -> int:
        """Wipe the demo state (queued jobs survive — they are arq's keys)."""
        return await self._store.reset_demo_state()
