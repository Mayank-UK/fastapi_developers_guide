"""The shared demo reset: one POST, every demo state, honest per-area rows.

A terminal-companion utility (no client panel by design): a reader
following the guide has mutated the running stack's demo state — toggled
the scenario, created posts, filled the cache, walked the shared
counter, parked dead letters — and wants the baseline back with one
call. The use case orchestrates participants the composition root
wires, every one through a reset path the area ALREADY owns (the
scenario store's ``reset``, the posts adapter's reseed, the caching
lab's ``invalidate``, the shared counter's ``delete``, the jobs
console's ``reset``, the PII store's ``reset``, the log ring's
``clear``) — no new business logic anywhere, only existing seams.

Honesty rules, in the family's grain. Every reset row carries the REAL
result of this request's action — counts and key names from the call
that just ran, never a claim. A participant behind an unreachable
optional store (Redis down) degrades to a ``degraded`` row naming the
failure instead of failing the whole reset — the other areas still
reset; anything that is not an ``AppError`` propagates (nothing is
swallowed). And the report says what it deliberately does NOT touch:
PostgreSQL tables + Alembic history, MongoDB collections, and the
messaging lab's Redis Streams history — destructive database resets are
out of scope, and saying so in the payload beats surprising a reader
who expected them.
"""

from collections.abc import Awaitable, Callable, Sequence
from typing import Final, Literal, NamedTuple

import structlog

from guide.core.errors import AppError
from guide.core.logging import recent_log
from guide.core.scenario import ScenarioStore
from guide.core.serialization import CamelModel
from guide.domain.caching.ports import CachedPosts
from guide.domain.demos.scaling_stateless import COUNTER_KEY
from guide.domain.jobs.service import JobsConsoleService
from guide.domain.scaling.ports import SharedCounterStore
from guide.domain.security.records import CustomerRecordStore

logger = structlog.get_logger()

ResetOutcome = Literal["reset", "degraded"]
"""What one area's action really achieved; ``degraded`` names the failure."""

ResetAction = Callable[[], Awaitable[str]]
"""One participant's action: run the existing reset path, report honestly."""


class ResetParticipant(NamedTuple):
    """One demo area: an id, a human label, and the existing reset path."""

    area: str
    label: str
    action: ResetAction


class ResetAreaRow(CamelModel):
    """One area's real result — counts and key names, never a claim."""

    area: str
    label: str
    outcome: ResetOutcome
    detail: str


class NotResetRow(CamelModel):
    """An area deliberately untouched, with a reason a reader can check."""

    area: str
    label: str
    reason: str


class ResetReport(CamelModel):
    """The whole reset: what returned to baseline, what never moved."""

    reset: list[ResetAreaRow]
    not_reset: list[NotResetRow]
    detail: str


NOT_RESET_AREAS: Final[tuple[NotResetRow, ...]] = (
    NotResetRow(
        area="postgres",
        label="PostgreSQL tables + Alembic history",
        reason=(
            "destructive database resets are out of scope — migrations are "
            "the deploy's job, and the db demos reseed idempotently through "
            "their own entry points"
        ),
    ),
    NotResetRow(
        area="mongo",
        label="MongoDB collections",
        reason=(
            "same destructive-scope rule — the mongo demo owns its "
            "guide_demo namespace and clears its own demo key every round"
        ),
    ),
    NotResetRow(
        area="redis-streams",
        label="Redis Streams history (messaging lab)",
        reason=(
            "the stream lab has no reset affordance — its stream, consumer "
            "group, and processed set are the demo's persistent substrate, "
            "not per-round state"
        ),
    ),
)
"""Scope made explicit in every report: these never move, on purpose."""


class DemoResetService:
    """Runs every participant's existing reset path; assembles the report."""

    def __init__(self, participants: Sequence[ResetParticipant]) -> None:
        """Hold the composition root's wiring; nothing runs until asked."""
        self._participants: Final[tuple[ResetParticipant, ...]] = tuple(participants)

    async def run(self) -> ResetReport:
        """Reset every area; an ``AppError`` degrades its row and nothing else.

        Per-area isolation mirrors the optional-service discipline: one
        unreachable store must not cost the areas that owe it nothing.
        Any other exception is a bug, not a degraded demo — it propagates
        to the shared handlers as the 500 envelope, swallowed by no one.
        """
        rows: list[ResetAreaRow] = []
        for participant in self._participants:
            try:
                detail = await participant.action()
            except AppError as exc:
                rows.append(
                    ResetAreaRow(
                        area=participant.area,
                        label=participant.label,
                        outcome="degraded",
                        detail=f"not reset — {exc.kind}: {exc.message}",
                    )
                )
                continue
            rows.append(
                ResetAreaRow(
                    area=participant.area,
                    label=participant.label,
                    outcome="reset",
                    detail=detail,
                )
            )
        degraded = sum(1 for row in rows if row.outcome == "degraded")
        logger.info(
            "demo_reset_completed",
            areas=len(rows),
            degraded=degraded,
        )
        return ResetReport(
            reset=rows,
            not_reset=list(NOT_RESET_AREAS),
            detail=(
                "every reset row carries this request's real result; degraded "
                "rows name the failure instead of claiming a reset, and the "
                "not-reset rows are deliberate scope, not omissions"
            ),
        )


def build_demo_reset_service(
    *,
    scenario: ScenarioStore,
    reset_posts: Callable[[], int],
    counter: SharedCounterStore,
    caching: CachedPosts,
    jobs: JobsConsoleService,
    pii_records: CustomerRecordStore,
) -> DemoResetService:
    """Wire every participant over the reset path it already owns.

    The composition root's one call: each parameter is the instance the
    app already serves through, except the posts reseed — the data-layer
    adapter crosses as a bound method (``Callable[[], int]`` answering
    how many posts were discarded), because this domain module must not
    import the data layer, and the resource port deliberately carries no
    reset verb. The log ring is the process-global singleton the logging
    pipeline feeds (the obs viewer's precedent) — the one piece of demo
    state that is process-wide by design, so the factory resolves it the
    way every reader of it does. The observability participant runs LAST
    so the events the earlier participants logged are cleared too.
    """

    async def _reset_scenario() -> str:
        scenario.reset()
        state = scenario.get()
        return (
            f"scenario returned to dataMode={state.data_mode}, "
            f"injectFailure={state.inject_failure} — the constructor's baseline"
        )

    async def _reset_posts() -> str:
        discarded = reset_posts()
        return f"{discarded} posts discarded; the fixed 12-post seed restored"

    async def _reset_caching() -> str:
        row = await caching.invalidate()
        if row.deleted_entries:
            return (
                f"cache entry {row.key} deleted — the next read is a miss and "
                f"refills from the origin; the telemetry counters are "
                f"cumulative per process and not zeroed"
            )
        return (
            f"no entry under {row.key} — expired or never filled; the next "
            f"read still refills from the origin"
        )

    async def _reset_scaling() -> str:
        deleted = await counter.delete(COUNTER_KEY)
        if deleted:
            return f"shared counter key {COUNTER_KEY} deleted"
        return f"shared counter key {COUNTER_KEY} already absent"

    async def _reset_jobs() -> str:
        cleared = await jobs.reset()
        return (
            f"{cleared} demo entries cleared (trails, dead letters, mailbox, "
            f"ledger, heartbeat); queued jobs survive — they are arq's keys"
        )

    async def _reset_pii() -> str:
        reseeded = pii_records.reset()
        return f"PII demo records reseeded — {reseeded} synthetic customers"

    async def _reset_observability() -> str:
        ring = recent_log()
        ring.clear()
        return (
            f"log ring cleared ({ring.capacity}-event bound); events captured "
            f"after this point remain — this request's own access-log row "
            f"included"
        )

    return DemoResetService(
        (
            ResetParticipant("scenario", "Scenario store", _reset_scenario),
            ResetParticipant("posts", "Posts substrate", _reset_posts),
            ResetParticipant("caching", "Cache-aside lab", _reset_caching),
            ResetParticipant("scaling", "Shared counter", _reset_scaling),
            ResetParticipant("jobs", "Jobs console", _reset_jobs),
            ResetParticipant("security-pii", "PII lab records", _reset_pii),
            ResetParticipant("observability", "Log ring", _reset_observability),
        )
    )
