"""The saga: a distributed transaction as forward steps plus compensations.

A database gives you ACID transactions: BEGIN, do several writes, COMMIT
— all or nothing, one store, one connection. The moment a business
operation spans services (reserve the stock HERE, charge the card
THERE, book the shipment ELSEWHERE), no such transaction exists: there
is no BEGIN that reaches across processes. A SAGA is the standard
answer — decompose the operation into a sequence of local
transactions, each with its own compensating action, and if a later
step fails, run the compensations for every step that already
committed, in REVERSE order. The undo is not a rollback (the
intermediate writes are already visible to the world); it is more
business work — a refund, a release, a cancellation — which is why
each compensation must exist BEFORE the forward step that needs it.

``SagaCoordinator`` is that pattern as pure orchestration, exactly as
testable as the circuit breaker beside it: the caller supplies the
definition (named steps, each naming its compensation), an EFFECTS
table (a callable per action/compensation name returning one evidence
line), and an injected clock, so a full run — four forwards commit; a
failed third step triggers compensations for two, newest-first — is a
unit test with integer inputs. An effect signals failure by raising
``SagaStepFailure`` (anything else raised is recorded as a failure
too — the run log keeps the repr, nothing is swallowed). A failing
COMPENSATION is recorded and the undo continues: the coordinator must
keep unwinding older steps even when one compensation refuses, the
same best-effort honesty the outbox relay teaches on its crash window.

The coordinator deliberately does NOT own durability: in production a
saga's steps are outbox events (topic 22's relay delivers them
at-least-once) and the saga log is itself an event stream, so a
coordinator that dies mid-run is replaced by one that reads its own
history forward. This module is the decision core that such a durable
runner embeds — the same relationship the pure retry policy has to
the arq worker that executes its verdicts.
"""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final, Literal, final

Clock = Callable[[], float]
"""Monotonic seconds, injected at construction — tests inject counters
(the circuit breaker's discipline: sequence proofs are integer math,
never timed sleeps)."""

SagaPhase = Literal["forward", "compensate"]
"""Which direction one log entry ran: forward progress, or the undo."""

StepOutcome = Literal["done", "failed", "compensated", "compensation-failed"]
"""One step's verdict in the run log."""

RunOutcome = Literal["committed", "compensated"]
"""The run's verdict: everything done, or everything undone."""


class SagaStepFailure(Exception):
    """One forward action refused to complete; the message names the step.

    The typed channel an effect uses to fail its step. Any other
    exception an effect raises is treated the same way, recorded with
    its repr — the run log is the saga's audit trail, not a crash.
    """


@dataclass(frozen=True, slots=True)
class SagaStep:
    """One step of the definition: a forward action and its undo, named.

    ``action`` and ``compensates`` are keys into the caller's effects
    table; ``describes`` is one line of what the action does — the
    definition is the saga's DOCUMENT, readable without the effects.
    """

    action: str
    compensates: str
    describes: str


@dataclass(frozen=True, slots=True)
class SagaDefinition:
    """A named business operation as an ordered step list.

    Steps run in list order; compensations run over the COMPLETED steps
    in reversed list order. The definition carries no behavior — pairs
    of names — so it serializes, diffs, and reviews like the document
    it is (a reviewer reads the undo plan before the first forward
    step ever runs; that is the point).
    """

    name: str
    steps: tuple[SagaStep, ...]


@dataclass(frozen=True, slots=True)
class SagaLogEntry:
    """One line of the run's log: which step, which direction, what happened.

    ``evidence`` is the effect's own line (the balance it moved, the
    slot it took) or the coordinator's (the failure's repr) — the
    per-step proof the run really did the work it claims.
    """

    index: int
    phase: SagaPhase
    step: str
    outcome: StepOutcome
    evidence: str
    at: float


@dataclass(frozen=True, slots=True)
class SagaOutcome:
    """The whole run: verdict, log, and the compensation order as proof.

    ``compensation_order`` is the compensations in the order they RAN —
    reversed over the completed steps — so "the undo went
    newest-first" is checkable without parsing the log (the tests pin
    it exactly; the demo prints it as its headline).
    """

    definition: str
    outcome: RunOutcome
    entries: tuple[SagaLogEntry, ...]
    failure_step: str | None
    compensation_order: tuple[str, ...]
    detail: str


Effects = Mapping[str, Callable[[], str]]
"""The behavior half: action/compensation name -> run it, return one
evidence line. Real effects write to a store or call a service; the
coordinator only requires that they either return a line or raise."""


@final
class SagaCoordinator:
    """Run a definition forward; on failure, undo the completed steps.

    The whole pattern is this one ``run`` call plus the reversed loop:
    no sleeping, no I/O, no threads — the caller's effects decide
    whether this is a unit test or a real distributed operation.
    """

    def __init__(self, clock: Clock = time.monotonic) -> None:
        """Hold the clock; a coordinator is stateless between runs."""
        self._clock = clock

    def run(self, definition: SagaDefinition, effects: Effects) -> SagaOutcome:
        """Forward through the steps; the first failure turns the run around.

        Every forward step that completes is remembered; the moment one
        fails, the run stops going forward and compensates the
        completed steps newest-first. A committed run (every step done)
        has nothing to undo and says so.
        """
        entries: list[SagaLogEntry] = []
        completed: list[SagaStep] = []
        failure_step: str | None = None

        for step in definition.steps:
            entry_or_failure = self._forward(step, effects, len(entries))
            if isinstance(entry_or_failure, SagaStepFailure):
                failure_step = step.action
                entries.append(
                    SagaLogEntry(
                        index=len(entries),
                        phase="forward",
                        step=step.action,
                        outcome="failed",
                        evidence=entry_or_failure.args[0],
                        at=self._clock(),
                    )
                )
                break
            entries.append(entry_or_failure)
            completed.append(step)

        if failure_step is None:
            return SagaOutcome(
                definition=definition.name,
                outcome="committed",
                entries=tuple(entries),
                failure_step=None,
                compensation_order=(),
                detail=(
                    f"{definition.name}: all {len(definition.steps)} steps committed — "
                    "nothing to undo, the saga is complete"
                ),
            )

        undo_entries, undo_order = self._compensate_all(completed, effects, len(entries))
        entries.extend(undo_entries)
        undo_line = " then ".join(undo_order) if undo_order else "nothing to undo"
        return SagaOutcome(
            definition=definition.name,
            outcome="compensated",
            entries=tuple(entries),
            failure_step=failure_step,
            compensation_order=undo_order,
            detail=(
                f"{definition.name}: step {failure_step!r} failed after "
                f"{len(completed)} completed step(s) — {len(undo_order)} compensation(s) "
                f"ran newest-first: {undo_line}"
            ),
        )

    def _forward(
        self, step: SagaStep, effects: Effects, index: int
    ) -> SagaLogEntry | SagaStepFailure:
        """Run one forward effect; a done-entry, or the failure to record."""
        try:
            evidence = effects[step.action]()
        except SagaStepFailure as failure:
            return failure
        except Exception as unexpected:  # recorded as data, never swallowed
            return SagaStepFailure(
                f"step {step.action!r} raised {type(unexpected).__name__}: {unexpected}"
            )
        return SagaLogEntry(
            index=index,
            phase="forward",
            step=step.action,
            outcome="done",
            evidence=evidence,
            at=self._clock(),
        )

    def _compensate_all(
        self, completed: list[SagaStep], effects: Effects, index: int
    ) -> tuple[list[SagaLogEntry], tuple[str, ...]]:
        """Undo the completed steps in REVERSE order, recording each.

        A compensation that raises is recorded as ``compensation-failed``
        and the undo CONTINUES with the older steps — the coordinator
        never leaves newer work undone because an undo refused. In a
        durable deployment these failures are retried by the runner;
        here the run log is the record that names them.
        """
        entries: list[SagaLogEntry] = []
        order: list[str] = []
        for step in reversed(completed):
            outcome: StepOutcome = "compensated"
            try:
                evidence = effects[step.compensates]()
            except Exception as failure:  # recorded as data, never swallowed
                outcome = "compensation-failed"
                evidence = (
                    f"compensation {step.compensates!r} raised "
                    f"{type(failure).__name__}: {failure}"
                )
            entries.append(
                SagaLogEntry(
                    index=index + len(entries),
                    phase="compensate",
                    step=step.compensates,
                    outcome=outcome,
                    evidence=evidence,
                    at=self._clock(),
                )
            )
            order.append(step.compensates)
        return entries, tuple(order)


DEMO_ORDER_SAGA: Final = SagaDefinition(
    name="order-fulfillment",
    steps=(
        SagaStep(
            action="reserve-item",
            compensates="release-item",
            describes="hold one unit of stock locally (a real transaction)",
        ),
        SagaStep(
            action="charge-card",
            compensates="refund-card",
            describes="take payment at the payment service",
        ),
        SagaStep(
            action="book-shipment",
            compensates="cancel-shipment",
            describes="reserve a delivery slot at the carrier",
        ),
        SagaStep(
            action="announce-order",
            compensates="retract-announce",
            describes="publish the order-confirmed event",
        ),
    ),
)
"""The demo's definition: the classic four-step fulfillment saga —
small enough to read at a glance, real enough that every compensation
is a genuinely different piece of business work."""
