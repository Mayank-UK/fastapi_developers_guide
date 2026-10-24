"""The structured-log viewer payload: the real pipeline + the real ring.

``GET /api/demo/obs/viewer`` serves this payload INLINE in topic 33's
structlog-JSON section. The panel is honest by construction: the pipeline
rows are INTROSPECTED from the process's live structlog configuration
(``structlog.get_config`` — the same chain every log call in this app
traverses, the middleware-stack-walk precedent), and every event row is a
REAL structured event the process logged — snapshotted by the
``RecentLog.capture`` processor ``configure_logging`` installs. With topic
33's access-log layer in the stack, ordinary traffic keeps the ring warm:
every request adds one ``http_request`` row, every failed request adds its
failure row beside it, both stamped with the request id.

The panel request also logs TWO of its own beats through the real pipeline
(``obs_viewer_panel_opened`` at info, one clearly-labeled sample warning)
before reading the tail — so the panel always demonstrates itself: its own
request id, the one this response's ``x-request-id`` header echoes, rides
on both rows. Nothing is staged: the events really render to stdout too.
"""

import structlog

from guide.core.logging import RecentEvent, recent_log
from guide.core.serialization import CamelModel

logger = structlog.get_logger()

_PIPELINE_ROLES: dict[str, str] = {
    "merge_contextvars": (
        "merges the request-scoped bound context — the request id the "
        "request-id middleware binds — into every event"
    ),
    "add_log_level": "stamps the level key every line carries",
    "TimeStamper": "adds the ISO-8601 timestamp",
    "ExceptionRenderer": "folds exception tracebacks into the event",
    "RecentLog.capture": (
        "snapshots the event into the recent-events ring — this panel's own "
        "substrate, the last step before rendering"
    ),
    "JSONRenderer": (
        "renders the dict as one JSON object per line — the line stdout receives"
    ),
}
"""One-line roles for the processors this app's chain is known to contain."""

_UNKNOWN_PROCESSOR_ROLE: str = "a structlog processor in the active chain"


class EventField(CamelModel):
    """One key/value pair of a structured event, rendered for display."""

    name: str
    value: str


class CapturedEvent(CamelModel):
    """One real event from the ring; wire is camelCase.

    ``request_id`` is the correlation key — empty when the event carries
    none (startup warnings, background work outside any request).
    """

    sequence: int
    """Ring-wide, strictly increasing — the capture order."""

    level: str
    event: str
    request_id: str
    timestamp: str
    fields: list[EventField]


class PipelineStage(CamelModel):
    """One processor of the ACTIVE chain, in execution order."""

    order_index: int
    processor: str
    role: str


class LogViewerPanel(CamelModel):
    """Wire shape of ``GET /api/demo/obs/viewer`` — the viewer's contract."""

    configured_level: str
    level_source: str
    ring_capacity: int
    pipeline: list[PipelineStage]
    events: list[CapturedEvent]
    panel_request_id: str
    pipeline_note: str
    honesty_note: str


PIPELINE_NOTE: str = (
    "The active pipeline, introspected live from structlog's process "
    "configuration — the same chain every log call in this app traverses, "
    "in execution order. The capture row is what feeds the ring below."
)

HONESTY_NOTE: str = (
    "Every row was really logged by this process through that pipeline — the "
    "two obs_viewer rows are this very request's own beats; http_request rows "
    "are the access-log layer's one line per request; http_exception and "
    "request_validation_failed rows are real failures other requests hit. The "
    "ring is process-local and bounded (a real log viewer reads aggregated "
    "stdout) — the rendered JSON lines themselves are what the terminal "
    "companion's docker logs stop shows."
)

LEVEL_SOURCE: str = "FDG_LOG_LEVEL env → AppConfig.log_level (default: info)"


def _processor_name(processor: object) -> str:
    """A bound method's qualified name, a function's name, else the class."""
    qualname = getattr(processor, "__qualname__", None)
    if isinstance(qualname, str) and qualname:
        return qualname
    return type(processor).__name__


def captured_event(event: RecentEvent) -> CapturedEvent:
    """Lift one ring snapshot into its wire shape (the trace demo reuses this)."""
    return CapturedEvent(
        sequence=event.sequence,
        level=event.level,
        event=event.event,
        request_id=event.request_id,
        timestamp=event.timestamp,
        fields=[EventField(name=name, value=value) for name, value in event.fields],
    )


def _pipeline_stages() -> list[PipelineStage]:
    """Introspect the ACTIVE processor chain from structlog's own config."""
    stages: list[PipelineStage] = []
    for index, processor in enumerate(structlog.get_config()["processors"]):
        name = _processor_name(processor)
        stages.append(
            PipelineStage(
                order_index=index,
                processor=name,
                role=_PIPELINE_ROLES.get(name, _UNKNOWN_PROCESSOR_ROLE),
            )
        )
    return stages


def build_log_viewer_payload(*, request_id: str, configured_level: str) -> LogViewerPanel:
    """Build the live viewer: real pipeline, real ring, this request's beats.

    Emits the panel's own two beats through the REAL logger first (info +
    a clearly-labeled warning, both stamped with ``request_id`` — the id
    this response's header echoes), then reads the ring's tail. The beats
    exist so a second level is visible even on a quiet process; they are
    real events — rendered to stdout and captured like any other.
    """
    ring = recent_log()
    logger.info(
        "obs_viewer_panel_opened",
        request_id=request_id,
        panel="obs:viewer",
        ring_capacity=ring.capacity,
    )
    logger.warning(
        "obs_viewer_sample_warning",
        request_id=request_id,
        detail="this panel's own warning-level beat — emitted so a second "
        "level is visible even on a quiet process",
    )
    return LogViewerPanel(
        configured_level=configured_level,
        level_source=LEVEL_SOURCE,
        ring_capacity=ring.capacity,
        pipeline=_pipeline_stages(),
        events=[captured_event(event) for event in ring.tail(ring.capacity)],
        panel_request_id=request_id,
        pipeline_note=PIPELINE_NOTE,
        honesty_note=HONESTY_NOTE,
    )
