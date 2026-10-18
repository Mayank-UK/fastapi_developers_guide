"""The read-modify-write race demo payloads: lost update vs lock.

``GET /api/demo/db/race`` serves these payloads — topic 17's isolation
demo. The adapter choreographs two concurrent transactions over the same
post's comment count twice (deterministic interleave — every statement
is awaited in a fixed order, no sleeps): unlocked, both transactions
read the same count and both write the SAME next slot (the lost
update), then locked with SELECT ... FOR UPDATE, where the second
transaction blocks until the first commits and computes from a fresh
read. This pure builder reads the slot numbers back out of the final
states and writes each run's verdict.
"""

import re

from guide.core.serialization import CamelModel
from guide.domain.db.ports import RaceOutcome, RaceRunRow, RaceSlotRow

_SLOT_NUMBER = re.compile(r"slot #(\d+)")


class RaceRunCard(CamelModel):
    """One run: choreography timeline, final comments, verdict."""

    mode: str
    timeline: list[str]
    final_slots: list[RaceSlotRow]
    verdict: str


class RacePayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/race``."""

    post_id: int
    post_title: str
    baseline_comments: int
    unlocked: RaceRunCard
    locked: RaceRunCard
    reasoning: str


def slot_numbers(slots: list[RaceSlotRow]) -> list[int]:
    """The slot number each surviving comment claims (pure)."""
    numbers: list[int] = []
    for slot in slots:
        match = _SLOT_NUMBER.search(slot.body)
        if match is not None:
            numbers.append(int(match.group(1)))
    return numbers


def _unlocked_verdict(slots: list[RaceSlotRow]) -> str:
    numbers = slot_numbers(slots)
    if len(numbers) > 1 and len(set(numbers)) == 1:
        return (
            f"LOST UPDATE: both transactions wrote slot #{numbers[0]} — "
            "the number the second one SHOULD have computed was never "
            "assigned. No error was raised anywhere; the count and the "
            "insert simply were not one atomic step."
        )
    if not numbers:
        return "No race residue found — the run left no comments behind."
    return f"Final slots: {numbers}."


def _locked_verdict(slots: list[RaceSlotRow]) -> str:
    numbers = slot_numbers(slots)
    if len(numbers) >= 2 and numbers == sorted(set(numbers)):
        return (
            f"SERIALIZED: the lock ordered the runs — slots "
            f"{numbers[0]} and {numbers[1]} both exist because the "
            "second COUNT executed after the first COMMIT made its "
            "insert visible. FOR UPDATE bought correctness at the "
            "price of waiting."
        )
    if not numbers:
        return "No race residue found — the run left no comments behind."
    return f"Final slots: {numbers}."


def _card(run: RaceRunRow, verdict: str) -> RaceRunCard:
    return RaceRunCard(
        mode=run.mode,
        timeline=run.timeline,
        final_slots=run.final_slots,
        verdict=verdict,
    )


def build_race_payload(outcome: RaceOutcome) -> RacePayload:
    """Shape both runs side by side with their verdicts (pure)."""
    return RacePayload(
        post_id=outcome.post_id,
        post_title=outcome.post_title,
        baseline_comments=outcome.baseline_comments,
        unlocked=_card(outcome.unlocked, _unlocked_verdict(outcome.unlocked.final_slots)),
        locked=_card(outcome.locked, _locked_verdict(outcome.locked.final_slots)),
        reasoning=(
            f"Both runs raced over the same post ({outcome.post_title!r}, "
            f"baseline {outcome.baseline_comments} comments) under READ "
            "COMMITTED — PostgreSQL's default, where every statement sees "
            "a fresh snapshot but nothing protects a read followed later "
            "by a write. The unlocked run lost an update silently; the "
            "locked run serialized on the row lock. Same schema, same "
            "statements, same isolation level — the only difference is "
            "who is allowed to compute while the row is contested."
        ),
    )
