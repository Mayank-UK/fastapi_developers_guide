"""UUID-lab builder tests: the ordering proofs, minted from a fixed clock."""

from guide.domain.demos.uuid_lab import build_uuid_lab_payload


def _payload(sample_count: int = 12):
    return build_uuid_lab_payload(now_ms=1_792_145_902_898, sample_count=sample_count)


def _run(payload, kind: str):
    return next(run for run in payload.runs if run.kind == kind)


def test_uuid7_run_sorts_in_generation_order() -> None:
    run = _run(_payload(), "uuid7")
    assert run.sort_ranks == list(range(12))
    assert run.sortable is True


def test_uuid4_run_does_not_sort_in_generation_order() -> None:
    run = _run(_payload(), "uuid4")
    assert run.sort_ranks != list(range(12))
    assert run.sortable is False


def test_sequence_run_falls_into_the_string_sort_trap() -> None:
    run = _run(_payload(), "sequence")
    # 1..12 minted in order; as TEXT "10" and "11" sort before "2".
    assert run.values[:2] == ["1", "2"]
    assert run.sortable is False
    assert sorted(run.values)[:4] == ["1", "10", "11", "12"]


def test_layout_dissects_a_real_uuid7_into_five_segments() -> None:
    payload = _payload()
    layout = payload.layout
    hex_value = layout.value.replace("-", "")
    assert sum(segment.bits for segment in layout.segments) == 128
    # The displayed slices concatenate back to the whole uuid hex.
    assert "".join(segment.hex_value for segment in layout.segments) == hex_value
    labels = [segment.label for segment in layout.segments]
    assert labels == ["unix_ms", "version", "rand_a", "variant", "rand_b"]
    assert layout.segments[0].bits == 48
    assert layout.segments[1].hex_value == "7"
    # The timestamp read back out matches the payload's clock reading.
    assert layout.unix_ms == 1_792_145_902_898
    assert layout.generated_at_iso.startswith("2026-10-16T")


def test_same_millisecond_uuid7s_share_a_long_hex_prefix() -> None:
    payload = _payload()
    assert len(payload.shared_prefix_hex) >= 12  # at least the time prefix
    first, second = _run(payload, "uuid7").values[:2]
    shared = ""
    for a, b in zip(first, second, strict=True):
        if a != b:
            break
        shared += a
    assert payload.shared_prefix_hex == shared


def test_strategy_cards_cover_the_three_candidates() -> None:
    payload = _payload()
    assert [card.id for card in payload.strategies] == ["sequence", "uuid4", "uuid7"]
    by_id = {card.id: card for card in payload.strategies}
    assert by_id["uuid7"].sortable_as_text is True
    assert by_id["uuid4"].sortable_as_text is False
    assert by_id["sequence"].random_bits == 0
    assert by_id["uuid7"].random_bits == 74


def test_every_run_mints_the_requested_sample_count() -> None:
    payload = _payload(sample_count=5)
    assert payload.sample_count == 5
    assert all(len(run.values) == 5 for run in payload.runs)
