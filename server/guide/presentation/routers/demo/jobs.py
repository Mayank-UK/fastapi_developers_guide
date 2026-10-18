"""The jobs console demo endpoints (area ``jobs``).

Thin routers (family invariant): every endpoint parses its input, calls
one service method, and maps the result — the retry decisions, the
catalog validation, and the snapshot assembly all live in the domain.
The one piece of starlette this router legitimately holds is the
BackgroundTasks comparison: it measures nothing itself — the service's
``fire_comparison`` schedules the in-process half through the injected
``background_tasks.add_task`` and enqueues the queued half, and both
halves file their own timings into the shared ledger.

Endpoint map (prefix ``/api/demo/jobs``):

- ``GET  /console``            — the panel (policy schedule, catalog, tour)
- ``POST /enqueue/{name}``     — enqueue a catalog task by name
- ``GET  /jobs/{job_id}``      — status + attempt trail + verdict
- ``GET  /stats``              — the two numbers (depth, oldest age)
- ``GET  /dlq``                — the parked jobs
- ``POST /dlq/{entry_id}/replay`` — re-enqueue fresh, entry kept as audit
- ``GET  /mailbox``            — the recorded emails
- ``POST /mailbox``            — compose + enqueue the email job
- ``GET  /heartbeat``          — the cron schedule's pulse
- ``POST /compare``            — fire both halves of one comparison run
- ``GET  /compare``            — the comparison ledger
- ``POST /reset``              — clear the demo lists (queued jobs survive)
"""

import time
from typing import Annotated, Final

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import Field

from guide.core.errors import AppError, FailureKind
from guide.core.serialization import CamelModel
from guide.domain.demos.jobs_console import JobsPanel, build_jobs_panel
from guide.domain.jobs.ports import (
    ComparisonRunRow,
    DeadLetterRow,
    EmailDraft,
    HeartbeatRow,
    JobSnapshotRow,
    JobTicket,
    MailboxRow,
    QueueStatsRow,
)
from guide.domain.jobs.service import JobsConsoleService

router = APIRouter(prefix="/api/demo/jobs", tags=["demo:jobs"])

CONSOLE_PATH: Final = "/console"
ENQUEUE_PATH: Final = "/enqueue/{name}"
JOB_PATH: Final = "/jobs/{job_id}"
STATS_PATH: Final = "/stats"
DLQ_PATH: Final = "/dlq"
DLQ_REPLAY_PATH: Final = "/dlq/{entry_id}/replay"
MAILBOX_PATH: Final = "/mailbox"
HEARTBEAT_PATH: Final = "/heartbeat"
COMPARE_PATH: Final = "/compare"
RESET_PATH: Final = "/reset"
"""The router's paths (prefix-relative) — the terminal companion names them."""


def get_jobs_service(request: Request) -> JobsConsoleService:
    """FastAPI dependency: the console service (wired in create_app)."""
    service = request.app.state.jobs_service
    if not isinstance(service, JobsConsoleService):
        raise AppError(FailureKind.INTERNAL, "jobs service not wired on app.state")
    return service


JobsDep = Annotated[JobsConsoleService, Depends(get_jobs_service)]


class EmailRequest(CamelModel):
    """The compose form's body — shape-checked at the boundary only.

    ``to`` is deliberately NOT address-validated here: the demo needs to
    be able to hand the WORKER a draft its own validation rejects, so
    the poison path (validate at the worker, dead-letter without one
    retry) is reachable live. The two-layer lesson: the boundary checks
    shape, the worker re-derives the contract — the queue has more
    doors than the router.
    """

    to: Annotated[str, Field(min_length=3, max_length=80)]
    subject: Annotated[str, Field(min_length=1, max_length=120)]
    body: Annotated[str, Field(max_length=2000)] = ""


class DeadLetterPanel(CamelModel):
    """Wire shape of ``GET /dlq`` — the parking lot plus its size."""

    entries: list[DeadLetterRow]
    detail: str


class MailboxPanel(CamelModel):
    """Wire shape of ``GET /mailbox`` — the recorded emails."""

    entries: list[MailboxRow]
    detail: str


class CompareFired(CamelModel):
    """Wire shape of ``POST /compare`` — both halves fired, honestly timed.

    ``handler_duration_ms`` is what THIS request cost (it contains the
    queued half's redis round trip — the in-process half cost only a
    list append); the ledger's two rows carry each half's
    decision-to-start handoff and work window.
    """

    run_id: str
    queued_job_id: str
    handler_duration_ms: float


class ComparisonPanel(CamelModel):
    """Wire shape of ``GET /compare`` — the recent runs, newest first."""

    runs: list[ComparisonRunRow]
    detail: str


class ResetDone(CamelModel):
    """Wire shape of ``POST /reset`` — how many demo keys were wiped."""

    cleared: int
    detail: str


@router.get(CONSOLE_PATH, response_model=JobsPanel)
async def read_console() -> JobsPanel:
    """The worker's front page: policy schedule, catalog, endpoint tour."""
    return build_jobs_panel()


@router.post(ENQUEUE_PATH, response_model=JobTicket, status_code=201)
async def enqueue_job(name: str, service: JobsDep) -> JobTicket:
    """Enqueue one catalog task — unknown names fail with the legal vocabulary."""
    return await service.enqueue(name)


@router.get(JOB_PATH, response_model=JobSnapshotRow)
async def read_job(job_id: str, service: JobsDep) -> JobSnapshotRow:
    """One job's story: key-layout status, the attempt trail, the verdict."""
    return await service.snapshot(job_id)


@router.get(STATS_PATH, response_model=QueueStatsRow)
async def read_stats(service: JobsDep) -> QueueStatsRow:
    """The two observability numbers, live from the queue's zset."""
    return await service.queue_stats()


@router.get(DLQ_PATH, response_model=DeadLetterPanel)
async def read_dlq(service: JobsDep) -> DeadLetterPanel:
    """The parked jobs — exhausted budgets and poison payloads alike."""
    return DeadLetterPanel(
        entries=await service.dead_letters(),
        detail="replay re-enqueues fresh: new job id, attempts reset to 1, "
        "entry kept as the audit record",
    )


@router.post(DLQ_REPLAY_PATH, response_model=JobTicket, status_code=201)
async def replay_dlq(entry_id: str, service: JobsDep) -> JobTicket:
    """Re-enqueue a parked job fresh — the operational loop's second chance."""
    return await service.replay(entry_id)


@router.get(MAILBOX_PATH, response_model=MailboxPanel)
async def read_mailbox(service: JobsDep) -> MailboxPanel:
    """The recorded emails — the demo's mailbox has no SMTP (topic 42 wires one)."""
    return MailboxPanel(
        entries=await service.mailbox(),
        detail="recorded by the worker's send_email task; no SMTP client here — "
        "the compose/send/record PATTERN is the lesson",
    )


@router.post(MAILBOX_PATH, response_model=JobTicket, status_code=201)
async def send_mail(request: EmailRequest, service: JobsDep) -> JobTicket:
    """Compose at the boundary, defer the send: the email-as-job flow.

    A ``to`` that is not an address is accepted on purpose — the worker
    parks it as poison, which is the demo's reachable no-retry path.
    """
    draft = EmailDraft(to=request.to, subject=request.subject, body=request.body)
    return await service.enqueue_email(draft)


@router.get(HEARTBEAT_PATH, response_model=HeartbeatRow)
async def read_heartbeat(service: JobsDep) -> HeartbeatRow:
    """The cron schedule's pulse — last beat and the running count."""
    return await service.heartbeat()


@router.post(COMPARE_PATH, response_model=CompareFired, status_code=201)
async def fire_comparison(
    background_tasks: BackgroundTasks, service: JobsDep
) -> CompareFired:
    """Same workload, two homes: BackgroundTasks after the response, arq in the worker.

    This is the repo's REAL BackgroundTasks usage — starlette runs the
    scheduled callable once the response has left the building, which is
    exactly the fire-and-forget contract (and its limit: the work lives
    only as long as the process does).
    """
    handler_started = time.perf_counter()
    run_id, ticket = await service.fire_comparison(background_tasks.add_task)
    return CompareFired(
        run_id=run_id,
        queued_job_id=ticket.job_id,
        handler_duration_ms=(time.perf_counter() - handler_started) * 1000,
    )


@router.get(COMPARE_PATH, response_model=ComparisonPanel)
async def read_comparison(service: JobsDep) -> ComparisonPanel:
    """The comparison ledger — poll until a run has both halves."""
    return ComparisonPanel(
        runs=await service.comparison_recent(),
        detail="handoff = decision-to-work-start (response flush vs queue "
        "pickup); work = the same paced workload both halves run",
    )


@router.post(RESET_PATH, response_model=ResetDone)
async def reset_demo(service: JobsDep) -> ResetDone:
    """Clear the demo lists — queued jobs survive (they are arq's keys)."""
    cleared = await service.reset()
    return ResetDone(
        cleared=cleared, detail="trails, dead letters, mailbox, ledger, heartbeat wiped"
    )
