"""The jobs ports: broker, dead letters, mailbox, heartbeat, comparison
runs, attempt trails — plus every row the console speaks.

Seven Protocols split the jobs world the way the engines need it:
``JobBroker`` enqueues and snapshots (status + attempt trail + the two
observability numbers), ``AttemptTrail`` is the per-job attempt log the
worker writes and the snapshot reads, ``DeadLetterQueue`` is the parking
lot and its replay, ``MailboxRecorder`` is the email-as-job sink,
``CronHeartbeat`` is the scheduling heartbeat, ``ComparisonRuns`` is the
BackgroundTasks-vs-queue ledger, and ``JobsReset`` clears the demo
state. ``JobsStore`` composes them all — the one dependency the console
service takes, implemented over one redis/arq pool in ``guide.data.jobs``
and over fakes in the unit tests.

Keys arrive fully formed (the family discipline): every key this area
touches is spelled in exactly one place here, and the adapters never
invent one.
"""

from typing import Annotated, Final, Literal, Protocol, runtime_checkable

from pydantic import Field

from guide.core.serialization import CamelModel

NAMESPACE: Final = "guide_demo:jobs:"
"""The jobs demos' key namespace root — this topic owns it exclusively."""

NAMESPACE_DISPLAY: Final = "guide_demo:jobs:*"
"""The namespace as the demo payloads display it (the playground's convention)."""

DLQ_KEY: Final = f"{NAMESPACE}dlq"
"""The dead-letter queue — a redis list of parked jobs, oldest first."""

MAILBOX_KEY: Final = f"{NAMESPACE}mailbox"
"""The email recorder — a redis list of delivered messages, oldest first."""

ATTEMPT_KEY_PREFIX: Final = f"{NAMESPACE}attempts:"
"""Per-job attempt trails — a redis list per job id, attempt order."""

HEARTBEAT_LAST_KEY: Final = f"{NAMESPACE}heartbeat:last"
"""The cron heartbeat's last run, as epoch milliseconds."""

HEARTBEAT_BEATS_KEY: Final = f"{NAMESPACE}heartbeat:beats"
"""The cron heartbeat's beat counter."""

COMPARISON_KEY: Final = f"{NAMESPACE}comparison"
"""The BackgroundTasks-vs-queue comparison ledger — a redis list."""

LIST_CAP: Final = 100
"""Longest any demo list grows before the oldest entries fall off (LTRIM)."""

PANEL_LIMIT: Final = 10
"""How many DLQ/mailbox/comparison rows a panel displays."""

JobStatusName = Literal[
    "deferred", "queued", "in_progress", "complete", "failed", "not_found"
]
"""The job lifecycle as the console reports it — arq's own states plus
the terminal split its result payload cannot give a decoded pool
(``complete`` vs ``failed`` comes from the attempt trail's last step)."""

AttemptOutcome = Literal["succeeded", "retry_scheduled", "failed_final"]
"""How one attempt ended: done, rescheduled by the policy, or dead-lettered."""

ComparisonSide = Literal["in_process", "queued"]
"""The comparison's two execution homes for the SAME workload."""


class JobLifecycleRow(CamelModel):
    """The key layout's live answer for one job id — arq's state machine, read.

    ``in_progress`` beats the queue (the entry was popped, the in-progress
    key is set); ``deferred``/``queued`` split on whether the zset score
    (the job's due time, in epoch ms) is still in the future;
    ``result_present`` means a terminal result key exists; ``gone`` means
    no key remembers the job at all.
    """

    state: Literal["in_progress", "deferred", "queued", "result_present", "gone"]
    score_ms: int | None


class JobTicket(CamelModel):
    """One enqueue's receipt: the id to poll and where it went."""

    job_id: str
    function_name: str
    enqueued_at_ms: int


class AttemptStepRow(CamelModel):
    """One attempt on the trail the worker writes per job: when, how it ended."""

    attempt: int
    outcome: AttemptOutcome
    detail: str
    at_ms: int


class JobSnapshotRow(CamelModel):
    """One job's whole story: lifecycle state, the attempt trail, the verdict.

    ``status`` follows the key layout first (in-progress beats the queue,
    a retained result means terminal), with the trail's last step
    splitting the terminal states; ``attempts`` is the trail in attempt
    order; ``result`` is the task's own words for what it did (or the
    dead-letter reason). ``dead_lettered`` is the trail's final verdict —
    a ``failed_final`` step is written only by the park-the-DLQ path, so
    the flag and the parking lot cannot disagree.
    """

    job_id: str
    status: JobStatusName
    attempts: list[AttemptStepRow]
    result: str | None = None
    dead_lettered: bool = False


class QueueStatsRow(CamelModel):
    """The two observability numbers: queue depth and the oldest job's age.

    ``oldest_age_seconds`` is ``None`` exactly when the queue is empty —
    an honest null, not a zero (an empty queue has no oldest job, and
    reporting 0 would read as "a fresh job is waiting").
    """

    depth: int
    oldest_age_seconds: float | None


class DeadLetterRow(CamelModel):
    """One parked job: why it died, how hard it was tried, its payload.

    ``replayed_as`` is the NEW job id a replay minted (replay re-enqueues
    fresh — new id, attempts reset to 1 — while this entry stays as the
    audit record of the original lineage).
    """

    entry_id: str
    job_id: str
    function_name: str
    attempts: int
    reason: str
    failed_at_ms: int
    payload: str
    replayed_as: str | None = None


class EmailDraft(CamelModel):
    """An email the worker will send — validated at the WORKER, not just the API.

    The boundary checks shape (lengths); this model adds the address rule
    (an ``@`` and a dotted domain), so a malformed address enqueued by
    ANY client — the API is not the only door into the queue — fails
    validation inside the task, classifies as poison, and dead-letters
    without spending one retry.
    """

    to: Annotated[str, Field(min_length=3, max_length=80)]
    subject: Annotated[str, Field(min_length=1, max_length=120)]
    body: Annotated[str, Field(max_length=2000)] = ""


class MailboxRow(CamelModel):
    """One recorded email — the demo's mailbox has no SMTP (topic 42 wires one)."""

    message_id: str
    to: str
    subject: str
    body: str
    sent_at_ms: int
    job_id: str


class HeartbeatRow(CamelModel):
    """The cron heartbeat: when it last beat, how many beats so far."""

    last_run_ms: int | None
    beats: int
    schedule: str


class ComparisonRunRow(CamelModel):
    """One side of one comparison run: where the work ran and how long.

    ``handoff_duration_ms`` is what the CALLER paid to hand the work off
    (a list append in-process, a redis round trip queued); the work
    window itself is ``work_duration_ms``.
    """

    run_id: str
    side: ComparisonSide
    ran_on: str
    handoff_duration_ms: float
    work_duration_ms: float
    finished_at_ms: int


def oldest_age_seconds(now_ms: int, oldest_score_ms: float | None) -> float | None:
    """The oldest queued job's age — pure, so the clamp is testable.

    A deferred retry's score sits in the FUTURE (its scheduled run
    time), so the honest age of a not-yet-due job is zero, never
    negative; an empty queue (``None``) has no oldest job at all.
    """
    if oldest_score_ms is None:
        return None
    return max(0.0, (now_ms - oldest_score_ms) / 1000)


# ── The ports ────────────────────────────────────────────────────────────────


@runtime_checkable
class JobBroker(Protocol):
    """Enqueue by catalog name and watch the queue — arq's client side."""

    async def enqueue(self, function_name: str, payload: str | None) -> JobTicket:
        """Enqueue one job; answer the receipt the caller polls with."""
        ...

    async def lifecycle(self, job_id: str) -> JobLifecycleRow:
        """One job's live state from the key layout (arq's own decision tree)."""
        ...

    async def queue_stats(self) -> QueueStatsRow:
        """The two numbers: queued depth and the oldest queued job's age."""
        ...


@runtime_checkable
class AttemptTrail(Protocol):
    """The per-job attempt log the worker writes and the snapshot reads."""

    async def note(self, job_id: str, step: AttemptStepRow) -> None:
        """Append one attempt's outcome to the job's trail."""
        ...

    async def steps(self, job_id: str) -> list[AttemptStepRow]:
        """The job's trail in attempt order (empty when nothing ran yet)."""
        ...


@runtime_checkable
class DeadLetterQueue(Protocol):
    """Where exhausted and poisoned jobs park, and how they leave."""

    async def record_dead_letter(self, entry: DeadLetterRow) -> None:
        """Park one job — the last attempt's verdict, in writing."""
        ...

    async def dead_letters(self, limit: int) -> list[DeadLetterRow]:
        """The parked jobs, newest first."""
        ...

    async def replay_dead_letter(self, entry_id: str) -> JobTicket:
        """Re-enqueue a parked job fresh — new id, attempts reset, entry kept."""
        ...

    async def dead_letter_size(self) -> int:
        """How many jobs are parked."""
        ...


@runtime_checkable
class MailboxRecorder(Protocol):
    """The email-as-job sink — records what a worker 'sent'."""

    async def record_message(self, message: MailboxRow) -> None:
        """File one delivered message."""
        ...

    async def messages(self, limit: int) -> list[MailboxRow]:
        """The mailbox, newest first."""
        ...

    async def mailbox_size(self) -> int:
        """How many messages the mailbox holds."""
        ...


@runtime_checkable
class CronHeartbeat(Protocol):
    """The scheduling heartbeat — proof the cron side of the worker lives."""

    async def beat(self) -> int:
        """Record one beat; answer the running beat count."""
        ...

    async def read(self) -> HeartbeatRow:
        """When the schedule last fired, and how often it has."""
        ...


@runtime_checkable
class ComparisonRuns(Protocol):
    """The ledger of the BackgroundTasks-vs-queue comparison."""

    async def record(self, run: ComparisonRunRow) -> None:
        """File one side of one run."""
        ...

    async def recent(self, limit: int) -> list[ComparisonRunRow]:
        """The recent runs, newest first."""
        ...


@runtime_checkable
class JobsReset(Protocol):
    """Clear the demo state — trails, dead letters, mailbox, ledger, beats."""

    async def reset_demo_state(self) -> int:
        """Wipe this namespace's demo keys (queued jobs survive — say so)."""
        ...


@runtime_checkable
class JobsStore(
    JobBroker,
    AttemptTrail,
    DeadLetterQueue,
    MailboxRecorder,
    CronHeartbeat,
    ComparisonRuns,
    JobsReset,
    Protocol,
):
    """Every jobs capability behind one store — the service's single port."""
