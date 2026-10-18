"""Structured logging setup (structlog, JSON).

``configure_logging()`` runs once from ``create_app()``; every line after
that renders as one JSON object with ``timestamp``, ``level``, and ``event``
keys — machine-greppable from day one. Request-id binding and richer
processors arrive with the observability topics.
"""

import logging

import structlog


def configure_logging(level: str) -> None:
    """Configure structlog's process-wide JSON pipeline; unknown levels fall
    back to INFO instead of crashing the app (config input is hostile)."""

    def _numeric_level(name: str) -> int:
        resolved = logging.getLevelName(name.upper())
        return resolved if isinstance(resolved, int) else logging.INFO

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_numeric_level(level)),
    )
