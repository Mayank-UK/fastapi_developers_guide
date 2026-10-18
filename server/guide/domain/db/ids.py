"""UUIDv7, implemented for real (RFC 9562) — time-ordered unique ids.

Python 3.13's ``uuid`` module has no ``uuid7`` — and that is the point:
the construction is simple enough to own, and owning it teaches the
layout. A UUIDv7 is 128 bits laid out as:

- unix_ms (48 bits) — milliseconds since the Unix epoch, leftmost, so
  the id SORTS as creation time;
- version (4 bits) — always ``7``;
- rand_a (12 bits) — a random base for the millisecond;
- variant (2 bits) — ``10`` (the RFC 9562 family);
- rand_b (62 bits) — a monotonic COUNTER in the top 42 bits, fresh
  randomness in the low 20, so ids minted in the SAME millisecond stay
  sortable and distinct.

``uuid7_from_parts`` is the pure assembler; ``Uuid7Mint`` is the stateful
minter that injects time and randomness (tests pass a fake clock); ``uuid7_timestamp_ms``
extracts the timestamp from any UUIDv7 — the round-trip proof.
"""

import secrets
import time
from collections.abc import Callable
from typing import Final
from uuid import UUID

UUID7_VERSION: Final[int] = 7
"""The version nibble that names the layout (RFC 9562, section 5.7)."""

_UNIX_MS_BITS: Final[int] = 48
_RAND_A_BITS: Final[int] = 12
_COUNTER_BITS: Final[int] = 42
_RANDOM_BITS: Final[int] = 20

_UNIX_MS_MASK: Final[int] = (1 << _UNIX_MS_BITS) - 1
_RAND_A_MASK: Final[int] = (1 << _RAND_A_BITS) - 1
_RAND_B_MASK: Final[int] = (1 << (_COUNTER_BITS + _RANDOM_BITS)) - 1

Clock = Callable[[], int]
"""Unix milliseconds on demand; production uses wall time, tests a fake."""


def uuid7_from_parts(unix_ms: int, rand_a: int, rand_b: int) -> UUID:
    """Assemble a UUIDv7 from its three fields (each taken mod its width).

    The version and variant bits are written here and only here — callers
    cannot forge another layout through this seam.
    """
    if unix_ms < 0:
        raise ValueError(f"unix_ms must be non-negative, got {unix_ms}")
    value = (unix_ms & _UNIX_MS_MASK) << 80
    value |= UUID7_VERSION << 76
    value |= (rand_a & _RAND_A_MASK) << 64
    value |= 0b10 << 62
    value |= rand_b & _RAND_B_MASK
    return UUID(int=value)


def uuid7_timestamp_ms(value: UUID) -> int:
    """Read the 48-bit unix-millisecond timestamp back out of a UUIDv7."""
    if value.version != UUID7_VERSION:
        raise ValueError(f"not a UUIDv7 (version {value.version}): {value}")
    return (value.int >> 80) & _UNIX_MS_MASK


def default_clock() -> int:
    """Wall-clock unix milliseconds (the production clock)."""
    return time.time_ns() // 1_000_000


class Uuid7Mint:
    """Mints monotonic UUIDv7s: one clock, one counter, thread-unsafe by design.

    Same-millisecond mints advance the counter in rand_b's top bits (the
    RFC's recommended monotonic method), so every mint is strictly greater
    than the last as a string. A clock that runs backwards is HELD at the
    last seen millisecond — monotonicity beats wall-time accuracy, and the
    counter keeps ids distinct while the clock catches up.
    """

    def __init__(self, clock: Clock = default_clock) -> None:
        self._clock = clock
        self._last_ms: int = -1
        self._counter: int = 0
        self._rand_a_base: int = 0

    def mint(self) -> UUID:
        """One fresh UUIDv7, greater than every previous mint from here."""
        now_ms = self._clock()
        if now_ms > self._last_ms:
            self._last_ms = now_ms
            self._counter = 0
            self._rand_a_base = secrets.randbelow(_RAND_A_MASK + 1)
        else:
            self._counter += 1
        rand_b = (self._counter << _RANDOM_BITS) | secrets.randbelow(1 << _RANDOM_BITS)
        return uuid7_from_parts(self._last_ms, self._rand_a_base, rand_b)
