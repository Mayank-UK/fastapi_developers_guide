"""Structured logging setup (structlog, JSON) + the recent-events ring.

``configure_logging()`` runs once from ``create_app()``; every line after
that renders as one JSON object with ``timestamp``, ``level``, and ``event``
keys — machine-greppable from day one. The observability topic (33) grew
the pipeline twice, additively: ``merge_contextvars`` runs first, so the
request id the request-id middleware binds as a structlog contextvar rides
on EVERY event without each call site passing it, and ``RecentLog.capture``
runs last before the renderer, so the process's most recent events are kept
in a bounded ring the structured-log viewer serves — the same events stdout
receives, snapshotted while they are still dicts.
"""

import json
import logging
import threading
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any, Final

import structlog

RECENT_EVENT_CAPACITY: Final[int] = 50
"""Events the ring holds: the LAST ones, oldest evicted first."""

_RESERVED_EVENT_KEYS: Final[frozenset[str]] = frozenset(
    {"event", "level", "timestamp", "request_id"}
)
"""Keys the ring lifts into named fields; every other key stays a field row."""


def _render_field(value: Any) -> str:
    """One display string per value: scalars verbatim, containers as JSON."""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str, sort_keys=True)


@dataclass(frozen=True)
class RecentEvent:
    """One structured event, snapshotted between the processors and the renderer.

    ``fields`` carries every event-dict key the ring does not lift into a
    named field, rendered as display strings — the same key/value pairs the
    JSON renderer writes to stdout.
    """

    sequence: int
    """Ring-wide, strictly increasing — the capture order, i.e. the truth."""

    level: str
    """The logging method used (debug/info/warning/error/exception/…)."""

    event: str
    """The event name — the snake_case key everything greps for."""

    timestamp: str
    """ISO-8601 stamp from the TimeStamper processor ("" if it never ran)."""

    request_id: str
    """The correlation key when the event carries one ("" otherwise)."""

    fields: tuple[tuple[str, str], ...]
    """Remaining key/value pairs, sorted by key for stable display."""


class RecentLog:
    """Bounded ring of the process's most recent structured events.

    Installed into the pipeline by ``configure_logging`` — the capture
    processor runs after ``format_exc_info`` (so tracebacks are folded in)
    and before ``JSONRenderer`` (so the event is still a dict). The lock is
    honesty, not ceremony: sync handlers run in the threadpool and can log
    while the event loop does (the SpanLog precedent). The ring is
    process-global BY DESIGN — logging itself is process-global state, and
    a per-app ring fed by a process-global pipeline would be a lie.
    """

    def __init__(self, capacity: int = RECENT_EVENT_CAPACITY) -> None:
        """Hold the last ``capacity`` events (at least one)."""
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._events: list[RecentEvent] = []
        self._lock = threading.Lock()
        self._next_sequence = 0

    @property
    def capacity(self) -> int:
        """The ring's bound (events held never exceed it)."""
        return self._capacity

    def capture(
        self, logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """structlog processor: snapshot the event, pass it through unchanged."""
        with self._lock:
            self._events.append(
                RecentEvent(
                    sequence=self._next_sequence,
                    level=method_name,
                    event=str(event_dict.get("event", "")),
                    timestamp=str(event_dict.get("timestamp", "")),
                    request_id=str(event_dict.get("request_id", "")),
                    fields=tuple(
                        (str(key), _render_field(value))
                        for key, value in sorted(event_dict.items())
                        if key not in _RESERVED_EVENT_KEYS
                    ),
                )
            )
            self._next_sequence += 1
            if len(self._events) > self._capacity:
                del self._events[: len(self._events) - self._capacity]
        return event_dict

    def tail(self, limit: int = 20) -> list[RecentEvent]:
        """The last ``limit`` events, oldest first (never the live list)."""
        with self._lock:
            return list(self._events[-limit:]) if limit > 0 else []

    def by_request_id(self, request_id: str) -> list[RecentEvent]:
        """Every held event carrying ``request_id``, oldest first."""
        if not request_id:
            return []
        with self._lock:
            return [event for event in self._events if event.request_id == request_id]

    def clear(self) -> None:
        """Drop held events (the sequence counter keeps counting); test isolation."""
        with self._lock:
            self._events = []


_recent_log: Final[RecentLog] = RecentLog()
"""The one ring the pipeline feeds — process-global, like logging itself."""


def recent_log() -> RecentLog:
    """The ring ``configure_logging`` installs (the viewer demo reads it)."""
    return _recent_log


def configure_logging(level: str) -> None:
    """Configure structlog's process-wide JSON pipeline; unknown levels fall
    back to INFO instead of crashing the app (config input is hostile).

    ``merge_contextvars`` runs first so the request id the request-id
    middleware binds as a structlog contextvar rides on every event; the
    ring capture runs last before rendering so the structured-log viewer can
    serve the process's recent events — identical to what stdout receives.
    """

    def _numeric_level(name: str) -> int:
        resolved = logging.getLevelName(name.upper())
        return resolved if isinstance(resolved, int) else logging.INFO

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            recent_log().capture,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_numeric_level(level)),
    )
