"""UUIDv7 property tests: the layout is the contract (RFC 9562).

Every load-bearing property of ``guide.domain.db.ids`` is pinned here:
version/variant bits, the bit layout of all three fields, timestamp
round-trip, same-millisecond monotonicity and distinctness (the
counter), clock-backwards holding, and the honest rejections.
"""

from uuid import UUID, uuid4

import pytest

from guide.domain.db.ids import (
    UUID7_VERSION,
    Uuid7Mint,
    default_clock,
    uuid7_from_parts,
    uuid7_timestamp_ms,
)


def test_version_and_variant_bits_are_uuid7() -> None:
    value = uuid7_from_parts(1_700_000_000_000, 0b1010_1010_1010, 0x0123_4567_89AB_CDEF)
    assert value.version == UUID7_VERSION
    assert value.variant == "specified in RFC 4122"  # the family with top bits 10


def test_bit_layout_places_each_field_where_the_rfc_says() -> None:
    unix_ms, rand_a, rand_b = 0xFFFF_FFFF_FFFF, 0xABC, 0x3FFF_FFFF_FFFF_FFFF
    value = uuid7_from_parts(unix_ms, rand_a, rand_b).int
    assert value >> 80 == unix_ms
    assert (value >> 76) & 0xF == UUID7_VERSION
    assert (value >> 64) & 0xFFF == rand_a
    assert (value >> 62) & 0b11 == 0b10
    assert value & ((1 << 62) - 1) == rand_b


def test_fields_are_masked_not_rejected() -> None:
    """Oversized inputs are taken mod their width — the assembler cannot overflow."""
    value = uuid7_from_parts((1 << 60) + 123, 0xFFFFF, (1 << 70) + 7)
    assert uuid7_timestamp_ms(value) == 123
    assert ((value.int >> 64) & 0xFFF) == (0xFFFFF & 0xFFF)
    assert (value.int & ((1 << 62) - 1)) == ((1 << 70) + 7) & ((1 << 62) - 1)


def test_timestamp_round_trip() -> None:
    unix_ms = 1_792_145_902_898
    assert uuid7_timestamp_ms(uuid7_from_parts(unix_ms, 1, 2)) == unix_ms


def test_negative_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        uuid7_from_parts(-1, 0, 0)


def test_timestamp_extraction_refuses_other_versions() -> None:
    with pytest.raises(ValueError, match="not a UUIDv7"):
        uuid7_timestamp_ms(uuid4())


def test_same_millisecond_mints_are_distinct_and_sorted() -> None:
    mint = Uuid7Mint(clock=lambda: 1_700_000_000_000)
    values = [str(mint.mint()) for _ in range(1000)]
    assert len(set(values)) == 1000
    # Strictly increasing as strings: sorted == generated, the index fact.
    assert sorted(values) == values


def test_mints_across_milliseconds_stay_sorted() -> None:
    now = {"ms": 1_700_000_000_000}
    mint = Uuid7Mint(clock=lambda: now["ms"])
    values = [str(mint.mint()) for _ in range(50)]
    now["ms"] += 1
    values += [str(mint.mint()) for _ in range(50)]
    assert sorted(values) == values


def test_clock_running_backwards_is_held_not_obeyed() -> None:
    ticks = iter([2_000_000_000_000, 1_999_999_999_999, 2_000_000_000_001])
    mint = Uuid7Mint(clock=lambda: next(ticks))
    first = mint.mint()
    second = mint.mint()  # clock went BACK one ms — must not regress
    third = mint.mint()
    assert str(first) < str(second) < str(third)
    assert uuid7_timestamp_ms(second) == 2_000_000_000_000


def test_default_clock_reads_wall_time_milliseconds() -> None:
    import time

    before = time.time_ns() // 1_000_000
    reading = default_clock()
    after = time.time_ns() // 1_000_000
    assert before <= reading <= after


def test_many_mints_from_many_clocks_never_collide() -> None:
    mints = [Uuid7Mint(clock=lambda: 1_700_000_000_000) for _ in range(20)]
    values = [str(m.mint()) for m in mints for _ in range(50)]
    assert len(set(values)) == len(values)


def test_uuid4_and_uuid7_share_the_uuid_surface() -> None:
    """Both are plain stdlib UUIDs — no wrapper type leaks out of the module."""
    assert isinstance(uuid7_from_parts(1, 0, 0), UUID)
