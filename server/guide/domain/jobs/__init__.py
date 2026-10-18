"""The jobs domain area: the retry policy, the catalog, the ports, the
console service, and the shared comparison workload.

Topic 29's subject, split the way it teaches: ``policy.py`` is the pure
retry engine (schedule, budget, poison classification — the webhook
topic's retry ideas, restated for a worker that owns longer-lived
reliability); ``catalog.py`` is the worker's registered task names as
the cross-process contract; ``ports.py`` is the whole vocabulary (seven
Protocols composed into ``JobsStore`` — broker, attempt trail, dead
letters, mailbox, heartbeat, comparison ledger, reset — plus every
result row and key constant); ``comparison.py`` is the SAME workload the
BackgroundTasks side and the queued side run; ``service.py`` is the
console's use cases and the shared DLQ parking flow. Everything here is
driver-free — redis and arq vocabulary never cross into the domain.
"""

from guide.domain.jobs.catalog import (
    DEMO_JOB_NAMES,
    JOB_CATALOG,
    JOB_COMPARISON_WORK,
    JOB_FAIL_ALWAYS,
    JOB_FAIL_ONCE,
    JOB_FAST,
    JOB_SEND_EMAIL,
    JOB_SLOW,
)
from guide.domain.jobs.comparison import run_comparison_work
from guide.domain.jobs.policy import (
    DEMO_JOB_POLICY,
    JobRetryPolicy,
    classify_failure,
    decide_retry,
)
from guide.domain.jobs.service import JobsConsoleService, park_dead_letter

__all__ = [
    "DEMO_JOB_NAMES",
    "DEMO_JOB_POLICY",
    "JOB_CATALOG",
    "JOB_COMPARISON_WORK",
    "JOB_FAIL_ALWAYS",
    "JOB_FAIL_ONCE",
    "JOB_FAST",
    "JOB_SEND_EMAIL",
    "JOB_SLOW",
    "JobRetryPolicy",
    "JobsConsoleService",
    "classify_failure",
    "decide_retry",
    "park_dead_letter",
    "run_comparison_work",
]
