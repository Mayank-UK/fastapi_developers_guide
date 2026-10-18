"""The ticker engine: determinism, the shared sequence, and the stream body.

The price walk is a PURE function of (symbol, seq) — same inputs, same
price, on every boot and every replay. The stream generator runs with an
instant injected sleeper and a fixed clock, so the frame sequence is
assertable byte for byte: ready, replay burst, paced ticks, keepalive
comments, the end frame, and the disconnect early-return.
"""

from guide.domain.realtime.ticker import (
    TICKER_SYMBOLS,
    TickerService,
    _mint_event,
    _price_at,
    stream_ticker_frames,
)


class InstantSleeper:
    """A sleeper that records waits and returns instantly."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def test_price_walk_is_deterministic_and_bounded() -> None:
    for symbol in TICKER_SYMBOLS:
        first = _price_at(symbol, 1)
        assert _price_at(symbol, 1) == first
    prices = [_price_at("FDG", seq) for seq in range(1, 61)]
    assert all(100.0 < price < 150.0 for price in prices)
    assert len(set(prices)) > 40  # it moves; it is not one constant


def test_minted_events_rotate_symbols_and_carry_change() -> None:
    events = [_mint_event(seq, at=0.0) for seq in range(1, 7)]
    assert [event.symbol for event in events] == ["FDG", "ASY", "PYC"] * 2
    fourth = events[3]  # FDG's second round: change compares against seq 1
    assert fourth.change == round(fourth.price - events[0].price, 2)


async def test_next_event_serializes_one_shared_sequence() -> None:
    service = TickerService(clock=lambda: 1.0)
    first = await service.next_event()
    second = await service.next_event()
    third = await service.next_event()
    assert (first.seq, second.seq, third.seq) == (1, 2, 3)
    stats = service.stats()
    assert stats.ticks_sent == 3
    assert stats.clients_served == 0


async def test_replay_after_counts_only_real_resumes() -> None:
    service = TickerService(clock=lambda: 1.0)
    for _ in range(4):
        await service.next_event()
    assert [event.seq for event in service.replay_after(2)] == [3, 4]
    assert service.stats().resume_replays == 1
    service.replay_after(9)  # current: not a resume
    assert service.stats().resume_replays == 1


async def test_stream_frames_ready_replay_ticks_end_in_order() -> None:
    service = TickerService(clock=lambda: 1.0)
    for _ in range(3):  # seq 1..3 exist before the client arrives
        await service.next_event()

    frames: list[str] = []
    async for frame in stream_ticker_frames(
        service,
        last_event_id=1,
        limit=2,
        pace_seconds=0.05,
        keepalive_every=0,
        sleeper=InstantSleeper(),
    ):
        frames.append(frame)

    assert frames[0].startswith("event: ready\nretry: 3000\n")
    assert '"replayed": 2' in frames[0]  # seq 2 and 3 replayed
    assert '"simulated": true' in frames[0]
    assert frames[1] == (
        "event: tick\nid: 2\ndata: " + _mint_event(2, at=1.0).model_dump_json() + "\n\n"
    )
    assert frames[2].startswith("event: tick\nid: 3\n")
    assert frames[3].startswith("event: tick\nid: 4\n")  # first live tick
    assert frames[4].startswith("event: tick\nid: 5\n")  # second live tick
    assert frames[5].startswith("event: end\n")
    assert '"liveTicks": 2' in frames[5]
    assert service.stats().clients_served == 1


async def test_stream_without_limit_runs_until_disconnect_probe_fires() -> None:
    service = TickerService(clock=lambda: 1.0)
    await service.next_event()

    async def probe_gone_after_two() -> bool:
        return service.stats().ticks_sent >= 3

    frames: list[str] = []
    async for frame in stream_ticker_frames(
        service,
        last_event_id=None,
        limit=0,
        pace_seconds=0.0,
        keepalive_every=0,
        sleeper=InstantSleeper(),
        is_disconnected=probe_gone_after_two,
    ):
        frames.append(frame)

    assert not any(frame.startswith("event: end") for frame in frames)
    live = [frame for frame in frames if frame.startswith("event: tick")]
    assert len(live) == 2  # stopped by the probe, not by a limit


async def test_keepalive_comments_interleave_on_the_counter() -> None:
    service = TickerService(clock=lambda: 1.0)
    frames: list[str] = []
    async for frame in stream_ticker_frames(
        service,
        last_event_id=None,
        limit=6,
        pace_seconds=0.0,
        keepalive_every=2,
        sleeper=InstantSleeper(),
    ):
        frames.append(frame)
    keepalives = [frame for frame in frames if frame.startswith(": keepalive")]
    ticks = [frame for frame in frames if frame.startswith("event: tick")]
    assert len(ticks) == 6
    assert len(keepalives) == 2  # after live ticks 2 and 4
    assert frames.index(keepalives[0]) < frames.index(ticks[2])


async def test_sleeper_receives_the_pace() -> None:
    service = TickerService(clock=lambda: 1.0)
    sleeper = InstantSleeper()
    async for _frame in stream_ticker_frames(
        service,
        last_event_id=None,
        limit=3,
        pace_seconds=0.25,
        keepalive_every=0,
        sleeper=sleeper,
    ):
        pass
    assert sleeper.waits == [0.25, 0.25, 0.25]
