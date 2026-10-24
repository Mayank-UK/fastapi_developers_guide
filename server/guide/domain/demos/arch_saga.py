"""The saga demo payload: two full runs of the REAL coordinator, with ledger proof.

``GET /api/demo/arch/saga`` serves this payload. The panel drives the
genuine ``SagaCoordinator`` from ``guide.domain.patterns.saga`` through
the four-step ``DEMO_ORDER_SAGA`` TWICE, against a per-request scratch
ledger the effects really mutate: the happy run commits all four steps;
the failing run injects a deterministic failure at ``book-shipment``
(the carrier is full) and proves the compensations ran in REVERSE
order over the two completed steps — refund-card, then release-item —
with per-step evidence lines the ledger itself produced. The balance
panel is the proof the undo really undid: stock, cents, and held slots
all return to their starting values, so a compensated run leaves the
same world it found (the failed step never wrote anything; the
never-reached step never ran).

Everything is deterministic: a fresh scratch ledger and a fresh
integer clock per request, no I/O, no sleeps — the injected failure is
a raise inside the step's own effect, the one honest way a step fails.
The durability row stays honest about what this panel is NOT: the
coordinator here is in-process, while a production saga survives
crashes because its steps ride the transactional outbox (topic 22) and
its run log is an event stream — the panel names that link, the topic
teaches it, and the outbox module is the repo's real durable half.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.patterns.saga import (
    DEMO_ORDER_SAGA,
    SagaCoordinator,
    SagaOutcome,
    SagaStepFailure,
)

FAILING_STEP: Final = "book-shipment"
"""The failing run's injected failure point — step 3 of 4, so TWO steps
need undoing (the interesting case: a reverse order over two)."""

FAILURE_REASON: Final = "carrier full: no delivery slot until Thursday"

PRICE_CENTS: Final = 4900
"""The demo order's price — 49.00 EUR in cents, integers everywhere."""


class SagaWorkflowStepRow(CamelModel):
    """One step of the definition as served: action, undo, one-line role."""

    action: str
    compensates: str
    describes: str


class SagaWorkflowRow(CamelModel):
    """The saga's definition — the document a reviewer reads before it runs."""

    name: str
    steps: list[SagaWorkflowStepRow]


class SagaEntryRow(CamelModel):
    """One run-log line: direction, step, verdict, the effect's own evidence."""

    index: int
    phase: str
    step: str
    outcome: str
    evidence: str
    at: str


class SagaRunRow(CamelModel):
    """One whole run: verdict, log, and (for the failing run) the undo proof."""

    label: str
    outcome: str
    failure_step: str | None = None
    compensation_order: list[str]
    detail: str
    entries: list[SagaEntryRow]


class SagaBalanceRow(CamelModel):
    """One scratch-ledger metric across both runs — the undo's arithmetic."""

    metric: str
    before: str
    after_happy: str
    after_failure: str
    verdict: str


class SagaDurabilityRow(CamelModel):
    """One half of how a real saga survives crashes (the honest link)."""

    half: str
    what: str
    where: str


class ArchSagaPanel(CamelModel):
    """Wire shape of GET /api/demo/arch/saga — both runs, the proof, the links."""

    workflow: SagaWorkflowRow
    happy_run: SagaRunRow
    failure_run: SagaRunRow
    balances: list[SagaBalanceRow]
    durability: list[SagaDurabilityRow]
    honesty_note: str


@dataclass
class _ScratchLedger:
    """The per-request world the effects mutate — four counters, start known.

    Real saga steps write to real stores; this ledger is those stores in
    miniature: deterministic, integer-valued, and printed by every
    effect's evidence line, so the panel's balances are READ BACK from
    the same world the coordinator changed.
    """

    stock: int = 2
    cents: int = 0
    slots_held: int = 0
    announcements: int = 0

    def snapshot(self) -> dict[str, int]:
        """A copy of the four counters — the balances rows read these."""
        return {
            "stock": self.stock,
            "cents": self.cents,
            "slots_held": self.slots_held,
            "announcements": self.announcements,
        }


@dataclass
class _Clock:
    """Integer clock rendered as T+lines — every entry's ``at`` is its order."""

    _ticks: int = field(default=0)

    def __call__(self) -> float:
        self._ticks += 1
        return float(self._ticks)


def _effects(ledger: _ScratchLedger, fail_at: str | None) -> dict[str, Callable[[], str]]:
    """Build the eight effects over ONE ledger: each returns its evidence line.

    The forward effects move the ledger and say what they moved (old ->
    new); the compensations move it back and say that. The step named by
    ``fail_at`` raises instead — the injected, deterministic failure
    point, raised by the step's own effect the way a real call fails.
    """

    def failing(action: str, reason: str) -> Callable[[], str]:
        def run() -> str:
            raise SagaStepFailure(f"{action} failed: {reason}")

        return run

    effects: dict[str, Callable[[], str]] = {}

    if fail_at == "reserve-item":
        effects["reserve-item"] = failing("reserve-item", "out of stock")
    else:

        def reserve() -> str:
            _dec(ledger, "stock")
            return f"stock widgets {ledger.stock + 1} -> {ledger.stock} (held for the order)"

        effects["reserve-item"] = reserve

    if fail_at == "charge-card":
        effects["charge-card"] = failing("charge-card", "card declined")
    else:

        def charge() -> str:
            _add(ledger, "cents", PRICE_CENTS)
            return f"balance {ledger.cents - PRICE_CENTS} -> {ledger.cents} cents (charged)"

        effects["charge-card"] = charge

    if fail_at == "book-shipment":
        effects["book-shipment"] = failing("book-shipment", FAILURE_REASON)
    else:

        def book() -> str:
            _inc(ledger, "slots_held")
            return f"carrier slot held ({ledger.slots_held} of 2 free slots taken)"

        effects["book-shipment"] = book

    if fail_at == "announce-order":
        effects["announce-order"] = failing("announce-order", "stream unreachable")
    else:

        def announce() -> str:
            _inc(ledger, "announcements")
            return f"order-confirmed event {ledger.announcements} published"

        effects["announce-order"] = announce

    def release() -> str:
        _inc(ledger, "stock")
        return f"stock widgets {ledger.stock - 1} -> {ledger.stock} (hold released)"

    def refund() -> str:
        _add(ledger, "cents", -PRICE_CENTS)
        return f"balance {ledger.cents + PRICE_CENTS} -> {ledger.cents} cents (refunded)"

    def cancel() -> str:
        _dec(ledger, "slots_held")
        return f"carrier slot released (held slots {ledger.slots_held + 1} -> {ledger.slots_held})"

    def retract() -> str:
        _dec(ledger, "announcements")
        return f"order-confirmed event {ledger.announcements + 1} retracted"

    effects["release-item"] = release
    effects["refund-card"] = refund
    effects["cancel-shipment"] = cancel
    effects["retract-announce"] = retract
    return effects


def _dec(ledger: _ScratchLedger, key: str) -> None:
    setattr(ledger, key, getattr(ledger, key) - 1)


def _inc(ledger: _ScratchLedger, key: str) -> None:
    setattr(ledger, key, getattr(ledger, key) + 1)


def _add(ledger: _ScratchLedger, key: str, delta: int) -> None:
    setattr(ledger, key, getattr(ledger, key) + delta)


def _run_row(label: str, outcome: SagaOutcome, entries_offset_note: str) -> SagaRunRow:
    """Map a coordinator outcome to its wire row (log lines verbatim)."""
    return SagaRunRow(
        label=label,
        outcome=outcome.outcome,
        failure_step=outcome.failure_step,
        compensation_order=list(outcome.compensation_order),
        detail=f"{outcome.detail} ({entries_offset_note})",
        entries=[
            SagaEntryRow(
                index=entry.index,
                phase=entry.phase,
                step=entry.step,
                outcome=entry.outcome,
                evidence=entry.evidence,
                at=f"T+{entry.at:.0f}",
            )
            for entry in outcome.entries
        ],
    )


def build_arch_saga_panel() -> ArchSagaPanel:
    """Run both saga runs fresh and shape the panel — pure, one call, no I/O."""
    workflow = SagaWorkflowRow(
        name=DEMO_ORDER_SAGA.name,
        steps=[
            SagaWorkflowStepRow(
                action=step.action, compensates=step.compensates, describes=step.describes
            )
            for step in DEMO_ORDER_SAGA.steps
        ],
    )

    happy_ledger = _ScratchLedger()
    happy = SagaCoordinator(clock=_Clock()).run(
        DEMO_ORDER_SAGA, _effects(happy_ledger, fail_at=None)
    )
    happy_after = happy_ledger.snapshot()

    failure_ledger = _ScratchLedger()
    failure = SagaCoordinator(clock=_Clock()).run(
        DEMO_ORDER_SAGA, _effects(failure_ledger, fail_at=FAILING_STEP)
    )
    failure_after = failure_ledger.snapshot()

    undo = failure.compensation_order
    balances = [
        SagaBalanceRow(
            metric="stock (widgets)",
            before="2",
            after_happy=str(happy_after["stock"]),
            after_failure=str(failure_after["stock"]),
            verdict=(
                "held by the happy run, released by the undo — back to the start"
                if failure_after["stock"] == 2
                else "UNEXPECTED"
            ),
        ),
        SagaBalanceRow(
            metric="balance (cents)",
            before="0",
            after_happy=str(happy_after["cents"]),
            after_failure=str(failure_after["cents"]),
            verdict=(
                "charged, then refunded newest-first — net zero"
                if failure_after["cents"] == 0
                else "UNEXPECTED"
            ),
        ),
        SagaBalanceRow(
            metric="carrier slots held",
            before="0",
            after_happy=str(happy_after["slots_held"]),
            after_failure=str(failure_after["slots_held"]),
            verdict=(
                "the failing step never wrote — nothing to undo for it"
                if failure_after["slots_held"] == 0
                else "UNEXPECTED"
            ),
        ),
        SagaBalanceRow(
            metric="announcements",
            before="0",
            after_happy=str(happy_after["announcements"]),
            after_failure=str(failure_after["announcements"]),
            verdict=(
                "the fourth step never ran — the run stopped at the failure"
                if failure_after["announcements"] == 0
                else "UNEXPECTED"
            ),
        ),
    ]

    durability = [
        SagaDurabilityRow(
            half="the steps",
            what=(
                "each step is a message the outbox delivers at-least-once — a "
                "coordinator death re-delivers, the idempotent consumer dedupes"
            ),
            where="guide/domain/messaging/outbox_service.py (topic 22)",
        ),
        SagaDurabilityRow(
            half="the run log",
            what=(
                "the saga's own history is an event stream — a restarted "
                "coordinator reads its log forward and resumes where it stopped"
            ),
            where="guide/domain/patterns/event_store.py (this topic's demo)",
        ),
    ]

    return ArchSagaPanel(
        workflow=workflow,
        happy_run=_run_row(
            "happy run",
            happy,
            "4 forward steps, 0 compensations — the business operation completed",
        ),
        failure_run=_run_row(
            f"failing run (injected failure at {FAILING_STEP})",
            failure,
            f"compensations ran newest-first: {' then '.join(undo)}",
        ),
        balances=balances,
        durability=durability,
        honesty_note=(
            "Both runs drove the real SagaCoordinator over a fresh scratch "
            "ledger on this request — the failure is an injected raise inside "
            "the step's own effect, never a faked log. This panel is the "
            "pattern's decision core in-process; a production saga adds the "
            "outbox's durability (see the durability rows) around exactly "
            "this coordinator."
        ),
    )
