"""The arq worker process: topic 29's separate-process answer (``guide.worker``).

This module is what ``arq guide.worker.WorkerSettings`` boots: the six
task functions the catalog names, the cron heartbeat, and the settings
class that binds them to redis. The tasks are deliberately SMALL and
quotable — each one is a behavior (succeed, fail once, fail always,
pace, send an email, run the comparison workload), and every retry
decision routes through the domain's pure policy: the task raises arq's
``Retry`` with the delay the policy computed, or parks the job in the
dead-letter queue when the verdict says the budget is spent — arq's
own ``max_tries`` is set to the same budget purely as a backstop.

One pool note: arq gives each task ``ctx["redis"]`` (its bytes-mode
pool, pickled payloads and all), but the adapter needs this repo's
decoded pool — so the worker keeps ONE ``ArqJobs`` store over its own
lazy pool, exactly like the server's, and never reads arq's pickles.
Two connections to one redis per worker process is the honest price of
one serialization rule.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import timedelta
from typing import Any, Final

from arq import Retry, cron
from arq.connections import RedisSettings

from guide.core.config import get_config
from guide.data.jobs import ArqJobs, create_arq_pool_factory
from guide.domain.jobs.catalog import SLOW_JOB_SECONDS
from guide.domain.jobs.comparison import QUEUED_HOME, run_comparison_work
from guide.domain.jobs.policy import DEMO_JOB_POLICY, classify_failure, decide_retry
from guide.domain.jobs.ports import (
    AttemptOutcome,
    AttemptStepRow,
    ComparisonRunRow,
    EmailDraft,
    MailboxRow,
)
from guide.domain.jobs.service import park_dead_letter

HEARTBEAT_FUNCTION: Final = "heartbeat"
"""The cron task's registered name (arq logs it beside every beat)."""

_store: ArqJobs | None = None
"""One store per worker process, built lazily over the worker's own pool."""


def _jobs() -> ArqJobs:
    """The worker's store — memoized so every task shares one decoded pool."""
    global _store
    if _store is None:
        _store = ArqJobs(create_arq_pool_factory(get_config()))
    return _store


def _now_ms() -> int:
    return int(time.time() * 1000)


async def _note(
    job_id: str, attempt: int, outcome: AttemptOutcome, detail: str
) -> None:
    """Append one attempt to the job's trail — the readable record."""
    await _jobs().note(
        job_id,
        AttemptStepRow(attempt=attempt, outcome=outcome, detail=detail, at_ms=_now_ms()),
    )


async def fast(ctx: dict[str, Any]) -> str:
    """The happy path: one attempt, immediate success, no retry spent."""
    job_id = str(ctx["job_id"])
    await _note(job_id, int(ctx["job_try"]), "succeeded", "done on the first try")
    return "succeeded on attempt 1 — the happy path"


async def fail_once(ctx: dict[str, Any]) -> str:
    """A transient failure: attempt 1 fails, the policy schedules attempt 2."""
    attempt = int(ctx["job_try"])
    delay = DEMO_JOB_POLICY.delay_before(attempt)
    if attempt == 1:
        await _note(
            str(ctx["job_id"]),
            attempt,
            "retry_scheduled",
            f"attempt 1 failed (simulated transient) — policy schedules "
            f"attempt 2 in {delay:.2f}s",
        )
        raise Retry(defer=timedelta(seconds=delay))
    await _note(
        str(ctx["job_id"]), attempt, "succeeded", "attempt 2 landed — the retry worked"
    )
    return f"succeeded on attempt {attempt} — one retry was enough"


async def fail_always(ctx: dict[str, Any]) -> str:
    """The budget's edge: every attempt fails until the last one dead-letters."""
    attempt = int(ctx["job_try"])
    verdict = decide_retry(DEMO_JOB_POLICY, attempt=attempt, failure_class="retryable")
    if verdict.action == "retry":
        await _note(str(ctx["job_id"]), attempt, "retry_scheduled", verdict.reason)
        assert verdict.delay_seconds is not None  # retry verdicts always carry one
        raise Retry(defer=timedelta(seconds=verdict.delay_seconds))
    await park_dead_letter(
        _jobs(),
        job_id=str(ctx["job_id"]),
        function_name="fail_always",
        attempts=attempt,
        reason=verdict.reason,
        payload="",  # fail_always takes no payload — replay re-enqueues it arg-less
        failed_at_ms=_now_ms(),
    )
    # A plain error (NOT Retry) is permanent — the trail says dead-lettered, arq says failed.
    raise RuntimeError(
        f"fail_always exhausted {attempt} attempts — parked in the dead-letter queue"
    )


async def slow(ctx: dict[str, Any]) -> str:
    """A paced workload (simulated and labeled): visible in the stats while it runs."""
    await asyncio.sleep(SLOW_JOB_SECONDS)
    await _note(
        str(ctx["job_id"]),
        int(ctx["job_try"]),
        "succeeded",
        f"paced workload finished ({SLOW_JOB_SECONDS:.1f}s, simulated)",
    )
    return f"slow job done after {SLOW_JOB_SECONDS:.1f}s of simulated pacing"


async def send_email(ctx: dict[str, Any], payload: str) -> str:
    """The classic deferred workload: validate at the worker, record the send.

    The payload is validated HERE (not just at the API): the queue is
    open to more doors than the router, so the worker re-derives the
    contract — and a malformed draft classifies as poison (the input is
    wrong), parking straight to the dead-letter queue without spending
    one retry. Topic 42 swaps the recorder for a real SMTP client; the
    PATTERN — compose, defer, send, record — is this topic's lesson.
    """
    try:
        draft = EmailDraft.model_validate_json(payload)
        _require_address(draft.to)
    except ValueError as exc:  # ValidationError derives from ValueError: both are poison
        verdict_reason = (
            f"failure classified {classify_failure(exc)}: payload rejected by the "
            "worker's own validation — retrying would re-ask the same broken question"
        )
        await park_dead_letter(
            _jobs(),
            job_id=str(ctx["job_id"]),
            function_name="send_email",
            attempts=int(ctx["job_try"]),
            reason=verdict_reason,
            payload=payload,
            failed_at_ms=_now_ms(),
        )
        raise ValueError("email payload is malformed — parked as poison") from exc
    message = MailboxRow(
        message_id=str(ctx["job_id"])[:8],
        to=draft.to,
        subject=draft.subject,
        body=draft.body,
        sent_at_ms=_now_ms(),
        job_id=str(ctx["job_id"]),
    )
    await _jobs().record_message(message)
    await _note(
        str(ctx["job_id"]),
        int(ctx["job_try"]),
        "succeeded",
        f"email to {draft.to} recorded in the mailbox",
    )
    return f"email to {draft.to} composed, 'sent', and recorded (no SMTP — topic 42)"


def _require_address(to: str) -> None:
    """The worker's address rule: an ``@`` and a dotted domain on its right."""
    if "@" not in to or "." not in to.rsplit("@", 1)[-1]:
        raise ValueError(f"{to!r} is not an address (needs @ and a dotted domain)")


async def comparison_work(ctx: dict[str, Any], payload: str) -> str:
    """The comparison's queued half: the same workload, in THIS process."""
    plan = json.loads(payload)
    work_started_ms = int(time.time() * 1000)
    work_seconds = await run_comparison_work(asyncio.sleep)
    await _jobs().record(
        ComparisonRunRow(
            run_id=str(plan["runId"]),
            side="queued",
            ran_on=QUEUED_HOME,
            handoff_duration_ms=work_started_ms - int(plan["decidedAtMs"]),
            work_duration_ms=work_seconds * 1000,
            finished_at_ms=_now_ms(),
        )
    )
    await _note(
        str(ctx["job_id"]),
        int(ctx["job_try"]),
        "succeeded",
        "comparison workload filed from the worker process",
    )
    return "comparison workload finished in the worker process"


async def heartbeat(ctx: dict[str, Any]) -> None:
    """The cron heartbeat: one beat a minute, plus one at boot for the tour."""
    await _jobs().beat()


class WorkerSettings:
    """The worker's whole configuration — what arq boots (and the tour quotes).

    ``functions`` is the name table the catalog mirrors (dispatch is by
    string); ``cron_jobs`` fires the heartbeat every minute and once at
    startup so the terminal tour never waits; ``max_tries`` equals the
    policy's budget as a BACKSTOP — the tasks themselves raise ``Retry``
    or dead-letter per the policy's verdicts first, so the backstop
    should never fire.
    """

    functions = [fast, fail_once, fail_always, slow, send_email, comparison_work]
    cron_jobs = [cron(heartbeat, minute=None, run_at_startup=True)]
    redis_settings = RedisSettings.from_dsn(get_config().redis_url)
    max_tries = DEMO_JOB_POLICY.max_attempts
    retry_jobs = True
    job_timeout = 30
