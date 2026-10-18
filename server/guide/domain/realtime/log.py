"""Bounded, seq-keyed event rings: the resumption source both protocols read.

Last-Event-ID replay (SSE) and ``?since=`` backfill (websocket chat) are
the same problem: a reconnecting client shows up with the sequence number
it last saw, and the server answers with everything after it — IF the
ring still holds a contiguous run from there. The honest edge is the
ring's start: a client that fell further behind than the capacity has
gapped, and gapped replay is a lie. ``events_after`` returns an empty
list for that case (and for "already current"), which the callers treat
as a FRESH START — the stream continues from now, never with a hole in
the middle. The bounded ``deque`` enforces the capacity mechanically:
appending past the limit silently drops the oldest event, exactly the
amnesia the replay semantics must account for.
"""

from collections import deque


class BoundedEventLog[T]:
    """Append-only ring of ``(seq, event)`` pairs with gap-aware replay."""

    def __init__(self, capacity: int) -> None:
        """Hold at most ``capacity`` events; the oldest drops on overflow."""
        if capacity < 1:
            raise ValueError("event log capacity must be at least 1")
        self._events: deque[tuple[int, T]] = deque(maxlen=capacity)

    def append(self, seq: int, event: T) -> None:
        """Record one event under its sequence number (caller guarantees order)."""
        self._events.append((seq, event))

    def events_after(self, last_seq: int) -> list[T]:
        """Everything after ``last_seq`` — or [] when a replay would be gapped.

        Three honest outcomes: nothing to send (empty ring, or the client is
        current); a contiguous replay (the event right after ``last_seq`` is
        still retained); or [] because retention no longer reaches back that
        far — the caller restarts the client from the present instead of
        replaying a hole.
        """
        if not self._events:
            return []
        oldest_seq = self._events[0][0]
        newest_seq = self._events[-1][0]
        if last_seq >= newest_seq:
            return []
        if last_seq + 1 < oldest_seq:
            return []  # the gap case: retention does not reach the client's position
        return [event for seq, event in self._events if seq > last_seq]

    def tail(self, count: int) -> list[T]:
        """The most recent ``count`` retained events (oldest-first).

        The scrollback shape: what a fresh connection sees as context, and
        the best-effort window served to a client whose ``since`` the ring
        can no longer reach.
        """
        if count >= len(self._events):
            return [event for _, event in self._events]
        return [event for _, event in list(self._events)[-count:]]

    @property
    def capacity(self) -> int:
        """The fixed retention limit."""
        return self._events.maxlen or 0

    @property
    def oldest_seq(self) -> int | None:
        """The oldest retained sequence number (None when empty)."""
        return self._events[0][0] if self._events else None

    @property
    def newest_seq(self) -> int | None:
        """The newest retained sequence number (None when empty)."""
        return self._events[-1][0] if self._events else None

    def __len__(self) -> int:
        """How many events are currently retained."""
        return len(self._events)
