"""The jobs console demo payload: the panel (demo ``jobs:console``).

Demo ``jobs:console`` (topic 29, INLINE in the retries section): the
panel is the worker's front page — the retry policy's exact schedule
(the offsets a fail-always walk runs at), the catalog of enqueueable
tasks with what each one teaches, the two observability numbers, the
dead-letter parking lot with its replay, the mailbox, the cron
heartbeat, and the BackgroundTasks-vs-queue comparison. All pure
shaping over the domain constants; the LIVE queue is the demo's real
centerpiece (every button lands on the real broker, the real worker,
the real dead letters).
"""

from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.jobs.catalog import (
    DEMO_JOB_NAMES,
    JOB_CATALOG,
    WORKER_COMMAND,
    JobSpec,
)
from guide.domain.jobs.policy import DEMO_JOB_POLICY
from guide.domain.jobs.ports import NAMESPACE_DISPLAY

QUEUE_NAMESPACE: Final = "arq:*"
"""arq's own keys (the queue zset, job/in-progress/result keys)."""


class EndpointRow(CamelModel):
    """One demo endpoint: the path and what trying it teaches."""

    path: str
    method: str
    teaches: str


class JobsPolicyRow(CamelModel):
    """The console's retry policy, exact: budget, curve, where attempts run."""

    max_attempts: int
    strategy: str
    base_delay_seconds: float
    delay_between_attempts: list[float]
    attempt_offsets: list[float]


class JobsPanel(CamelModel):
    """Wire shape of ``GET /api/demo/jobs/console`` — the panel's contract."""

    policy: JobsPolicyRow
    catalog: list[JobSpec]
    queue_keys: str
    demo_namespace: str
    worker_command: str
    cron_schedule: str
    endpoints: list[EndpointRow]
    honesty_notes: list[str]
    reasoning: str


def build_jobs_panel() -> JobsPanel:
    """The panel: policy schedule, task catalog, endpoint tour, honesty."""
    policy = DEMO_JOB_POLICY
    return JobsPanel(
        policy=JobsPolicyRow(
            max_attempts=policy.max_attempts,
            strategy=policy.strategy,
            base_delay_seconds=policy.base_delay_seconds,
            delay_between_attempts=[
                policy.delay_before(attempt)
                for attempt in range(1, policy.max_attempts)
            ],
            attempt_offsets=policy.attempt_offsets(),
        ),
        catalog=[JOB_CATALOG[name] for name in DEMO_JOB_NAMES],
        queue_keys=QUEUE_NAMESPACE,
        demo_namespace=NAMESPACE_DISPLAY,
        worker_command=WORKER_COMMAND,
        cron_schedule="heartbeat: every minute (arq cron) + once at worker boot",
        endpoints=[
            EndpointRow(
                path="/api/demo/jobs/enqueue/fast",
                method="POST",
                teaches="the happy path: enqueue, poll the job, watch one attempt succeed",
            ),
            EndpointRow(
                path="/api/demo/jobs/enqueue/fail_once",
                method="POST",
                teaches="the retry made visible: attempt 1 fails, the policy "
                "delays attempt 2, it lands",
            ),
            EndpointRow(
                path="/api/demo/jobs/enqueue/fail_always",
                method="POST",
                teaches="the full walk: three attempts on the curve, then the "
                "dead-letter queue",
            ),
            EndpointRow(
                path="/api/demo/jobs/stats",
                method="GET",
                teaches="the two observability numbers — queue depth and the oldest job's age",
            ),
            EndpointRow(
                path="/api/demo/jobs/dlq",
                method="GET",
                teaches="the parking lot; POST /dlq/{entry}/replay re-enqueues fresh",
            ),
            EndpointRow(
                path="/api/demo/jobs/compare",
                method="POST",
                teaches="same workload twice: starlette BackgroundTasks vs the arq worker",
            ),
        ],
        honesty_notes=[
            "every button lands on the real broker (redis) and the real worker "
            "process — nothing here is simulated except the paced workloads, "
            "which are labeled",
            "the worker is a separate container (compose service arq-worker) — "
            "stop it and the queue keeps accepting jobs the stats will show "
            "waiting",
            "attempt trails, dead letters, mailbox and ledger live under "
            f"{NAMESPACE_DISPLAY} and survive worker restarts (redis-backed)",
            "POST /api/demo/jobs/reset clears the demo lists; queued jobs "
            "survive (they are arq's keys, not the demo's)",
        ],
        reasoning=(
            "One policy engine decides every retry: tasks raise arq Retry with "
            "the delay it computed, or park the job in the dead-letter queue "
            "when the verdict says the budget is spent — arq's max_tries is "
            "the backstop, the domain is the decision."
        ),
    )
