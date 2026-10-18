"""UUID-lab demo payloads: uuid4 vs UUIDv7 vs bigserial, side by side.

``GET /api/demo/db/uuid`` serves these payloads — topic 16's second
demo. Three sample runs are minted per request: uuid4 (the stdlib
default), UUIDv7 (this repo's own implementation, ``guide.domain.db.ids``),
and a bigserial-style sequence (1, 2, 3, … — the numbers the posts
table's ``nextval`` default produces). For every run the payload proves
the ORDERING fact: ``sort_ranks`` maps each generated value to its rank
in lexicographic sort order, so UUIDv7 reads 0, 1, 2, … (sorted ==
generated) while uuid4 reads as noise and the sequence sorts only as
STRINGS ("10" before "2") — the exact reason sequential ids do not sort
as text. One UUIDv7 is additionally disassembled into its five RFC 9562
segments, hex slice by hex slice, and its timestamp is read back out —
the round-trip proof that the leftmost bits ARE time.

The builder is PURE: it takes the millisecond clock reading and the
sample count, mints everything through ``Uuid7Mint`` locally, and
shapes the payload — no I/O, no module state.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from guide.core.serialization import CamelModel
from guide.domain.db.ids import Uuid7Mint, uuid7_timestamp_ms


class SampleRun(CamelModel):
    """One strategy's freshly minted sample, with its ordering proof."""

    kind: str
    values: list[str]
    sort_ranks: list[int]
    sortable: bool


class UuidSegment(CamelModel):
    """One labeled slice of a UUIDv7's hex, as the layout reads left→right."""

    label: str
    hex_value: str
    bits: int
    meaning: str


class Uuid7Layout(CamelModel):
    """One real UUIDv7, disassembled: segments + the timestamp read back."""

    value: str
    unix_ms: int
    generated_at_iso: str
    segments: list[UuidSegment]


class UuidStrategyCard(CamelModel):
    """One id strategy's trade-offs, as the lab compares them."""

    id: str
    name: str
    sortable_as_text: bool
    index_locality: str
    random_bits: int | None
    coordination: str
    leaks_timing: bool


class UuidLabPayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/uuid``."""

    sample_count: int
    runs: list[SampleRun]
    shared_prefix_hex: str
    layout: Uuid7Layout
    strategies: list[UuidStrategyCard]
    reasoning: str


def _sort_ranks(values: list[str]) -> list[int]:
    """For each generated value (in order), its rank in sorted order.

    The identity permutation ``[0, 1, 2, …]`` means generation order IS
    sort order — the property that makes an id strategy index-friendly.
    """
    sorted_values = sorted(values)
    return [sorted_values.index(value) for value in values]


def _layout(uuid7_value: str) -> Uuid7Layout:
    """Disassemble one UUIDv7 hex string into its five RFC 9562 segments."""
    hex_value = uuid7_value.replace("-", "")
    unix_ms = uuid7_timestamp_ms(UUID(uuid7_value))
    return Uuid7Layout(
        value=uuid7_value,
        unix_ms=unix_ms,
        generated_at_iso=datetime.fromtimestamp(unix_ms / 1000, tz=UTC).isoformat(),
        segments=[
            UuidSegment(
                label="unix_ms",
                hex_value=hex_value[0:12],
                bits=48,
                meaning="milliseconds since the Unix epoch — leftmost, so the id sorts as time",
            ),
            UuidSegment(
                label="version",
                hex_value=hex_value[12:13],
                bits=4,
                meaning="always 7 — the nibble that names this layout",
            ),
            UuidSegment(
                label="rand_a",
                hex_value=hex_value[13:16],
                bits=12,
                meaning="a random base, redrawn when the millisecond ticks",
            ),
            UuidSegment(
                label="variant",
                hex_value=hex_value[16:17],
                bits=4,
                meaning="the TOP two bits are the RFC 9562 marker (so 8, 9, a, or b); "
                "the low two belong to rand_b's counter",
            ),
            UuidSegment(
                label="rand_b",
                hex_value=hex_value[17:32],
                bits=60,
                meaning="counter (top 42 bits) + randomness (low 20) — 62 bits total; "
                "its first two bits live in the variant nibble above",
            ),
        ],
    )


_STRATEGIES: tuple[UuidStrategyCard, ...] = (
    UuidStrategyCard(
        id="sequence",
        name="bigserial (sequence)",
        sortable_as_text=False,
        index_locality="perfect — every insert appends to the right edge",
        random_bits=0,
        coordination="the database mints it; single-writer per table",
        leaks_timing=True,
    ),
    UuidStrategyCard(
        id="uuid4",
        name="UUIDv4 (random)",
        sortable_as_text=False,
        index_locality="worst — inserts scatter across the whole B-tree",
        random_bits=122,
        coordination="none — anyone can mint one anywhere",
        leaks_timing=False,
    ),
    UuidStrategyCard(
        id="uuid7",
        name="UUIDv7 (time-ordered)",
        sortable_as_text=True,
        index_locality="good — new ids cluster near the right edge",
        random_bits=74,
        coordination="none — mint anywhere; time keeps them ordered",
        leaks_timing=True,
    ),
)


def build_uuid_lab_payload(*, now_ms: int, sample_count: int) -> UuidLabPayload:
    """Mint the three sample runs and shape the lab payload (pure)."""
    mint = Uuid7Mint(clock=lambda: now_ms)
    uuid7_values = [str(mint.mint()) for _ in range(sample_count)]
    uuid4_values = [str(uuid4()) for _ in range(sample_count)]
    sequence_values = [str(n) for n in range(1, sample_count + 1)]

    shared_prefix = ""
    if len(uuid7_values) >= 2:
        first, second = uuid7_values[0], uuid7_values[1]
        for a, b in zip(first, second, strict=True):
            if a != b:
                break
            shared_prefix += a

    return UuidLabPayload(
        sample_count=sample_count,
        runs=[
            SampleRun(
                kind="uuid4",
                values=uuid4_values,
                sort_ranks=_sort_ranks(uuid4_values),
                sortable=_sort_ranks(uuid4_values) == list(range(sample_count)),
            ),
            SampleRun(
                kind="uuid7",
                values=uuid7_values,
                sort_ranks=_sort_ranks(uuid7_values),
                sortable=_sort_ranks(uuid7_values) == list(range(sample_count)),
            ),
            SampleRun(
                kind="sequence",
                values=sequence_values,
                sort_ranks=_sort_ranks(sequence_values),
                sortable=_sort_ranks(sequence_values) == list(range(sample_count)),
            ),
        ],
        shared_prefix_hex=shared_prefix,
        layout=_layout(uuid7_values[0]),
        strategies=list(_STRATEGIES),
        reasoning=(
            f"All {sample_count} UUIDv7s were minted inside one millisecond and still "
            f"sort in generation order (their ranks read 0..{sample_count - 1}); they "
            f"share their first {len(shared_prefix)} hex digits ({shared_prefix or 'none'}) "
            "— the time prefix doing exactly that. The uuid4 run sorts randomly, and "
            "the sequence run, read as TEXT, puts '10' and '11' before '2' — the "
            "string-sort trap that disqualifies bigserial as a page cursor. Bigserial "
            "appends beautifully but counts rows per table and leaks timing; uuid4 "
            "hides timing but shatters B-tree locality; UUIDv7 buys uuid4's "
            "mint-anywhere freedom with sequence-grade ordering."
        ),
    )
