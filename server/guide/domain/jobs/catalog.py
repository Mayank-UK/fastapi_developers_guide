"""The job catalog: the worker's registered tasks, by name, with intent.

arq dispatches by FUNCTION NAME — the enqueuer says ``"fail_once"`` and
the worker looks that string up in its ``functions`` list, which makes
the name table the real contract between the two processes. This module
is that contract written down as data: every task the worker registers
appears here with its behavior (what an observer should watch happen)
and what trying it teaches. The demo router validates enqueue requests
against this table, so an unknown name fails at the boundary with the
catalog's own vocabulary in the error — never as a mystery job id that
quietly never runs.
"""

from typing import Final, Literal

from guide.core.serialization import CamelModel

JobBehavior = Literal[
    "succeeds-first-try",
    "succeeds-on-retry",
    "exhausts-retries",
    "paced",
    "email",
    "comparison",
]
"""What a job demonstrably does — the behavior axis the panel teaches along."""

JOB_FAST: Final = "fast"
JOB_FAIL_ONCE: Final = "fail_once"
JOB_FAIL_ALWAYS: Final = "fail_always"
JOB_SLOW: Final = "slow"
JOB_SEND_EMAIL: Final = "send_email"
JOB_COMPARISON_WORK: Final = "comparison_work"
"""The worker's registered task names — arq dispatches on these strings."""


class JobSpec(CamelModel):
    """One registered task: its name, its observable behavior, its lesson."""

    name: str
    behavior: JobBehavior
    expected_attempts: int
    paced_seconds: float | None = None
    takes_payload: bool = False
    teaches: str


_CATALOG_ROWS: Final[tuple[JobSpec, ...]] = (
    JobSpec(
        name=JOB_FAST,
        behavior="succeeds-first-try",
        expected_attempts=1,
        teaches="the happy path: one attempt, immediate success, no retry spent",
    ),
    JobSpec(
        name=JOB_FAIL_ONCE,
        behavior="succeeds-on-retry",
        expected_attempts=2,
        teaches="a transient failure: attempt 1 fails, the policy schedules "
        "attempt 2, the retry lands — watch the trail show both",
    ),
    JobSpec(
        name=JOB_FAIL_ALWAYS,
        behavior="exhausts-retries",
        expected_attempts=3,
        paced_seconds=None,
        teaches="the budget's edge: every attempt fails on the policy's curve "
        "until the last one parks the job in the dead-letter queue",
    ),
    JobSpec(
        name=JOB_SLOW,
        behavior="paced",
        expected_attempts=1,
        paced_seconds=2.0,
        teaches="a paced workload (simulated and labeled): visible in the queue "
        "stats while it waits and in the trail while it runs",
    ),
    JobSpec(
        name=JOB_SEND_EMAIL,
        behavior="email",
        expected_attempts=1,
        takes_payload=True,
        teaches="the classic deferred workload: compose at the boundary, send in "
        "the worker, record in the mailbox — or dead-letter as poison when "
        "the payload is malformed",
    ),
    JobSpec(
        name=JOB_COMPARISON_WORK,
        behavior="comparison",
        expected_attempts=1,
        takes_payload=True,
        teaches="the shared workload the BackgroundTasks comparison enqueues on "
        "its queued side (the in-process side runs the same function)",
    ),
)

JOB_CATALOG: Final[dict[str, JobSpec]] = {spec.name: spec for spec in _CATALOG_ROWS}
"""The name table — the enqueuer's only legal vocabulary."""

DEMO_JOB_NAMES: Final[tuple[str, ...]] = tuple(
    spec.name for spec in _CATALOG_ROWS if spec.behavior != "comparison"
)
"""The panel's enqueue buttons — every catalog task a human fires directly."""

SLOW_JOB_SECONDS: Final = 2.0
"""The paced job's simulated duration (the label the panel wears)."""

WORKER_COMMAND: Final = "arq guide.worker.WorkerSettings"
"""The command that boots the worker process — the panel quotes it, the
compose service runs it (the settings class it names is the binding)."""
