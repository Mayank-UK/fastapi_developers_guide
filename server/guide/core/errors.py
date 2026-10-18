"""Error taxonomy + the single HTTP error envelope, end to end.

One place owns every failure the app can produce: the eight ``FailureKind``
buckets, their HTTP statuses, the ``AppError`` exception layers raise, and the
camelCase envelope ``{"error": {code, message, requestId, details?}}`` every
client sees. Nothing outside this module invents status codes or error codes;
``register_exception_handlers`` maps AppError, FastAPI's request validation,
Starlette HTTPExceptions, and unhandled exceptions onto the same envelope.

Recorded family decisions:
- ``validation_failed`` → HTTP 422 (FastAPI-idiomatic; the express sibling
  uses 400 — deliberate divergence, taught in the validation topic).
- Starlette statuses the taxonomy does not name keep their truthful status
  and take the closest kind bucket: other 4xx → ``not_found`` (e.g. 405
  method-not-allowed), other 5xx → ``internal``.
- Unhandled exceptions log the traceback with the request id but respond with
  a generic message — internals never leak to clients.
"""

from enum import StrEnum
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from guide.core.request_context import resolve_request_id
from guide.core.serialization import CamelModel

logger = structlog.get_logger()

_GENERIC_INTERNAL_MESSAGE: str = "Internal server error."


class FailureKind(StrEnum):
    """The eight failure buckets every error in the app maps onto."""

    VALIDATION_FAILED = "validation_failed"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL = "internal"


_HTTP_STATUS_BY_KIND: dict[FailureKind, int] = {
    FailureKind.VALIDATION_FAILED: 422,
    FailureKind.UNAUTHORIZED: 401,
    FailureKind.FORBIDDEN: 403,
    FailureKind.NOT_FOUND: 404,
    FailureKind.CONFLICT: 409,
    FailureKind.RATE_LIMITED: 429,
    FailureKind.SERVICE_UNAVAILABLE: 503,
    FailureKind.INTERNAL: 500,
}

_KIND_BY_HTTP_STATUS: dict[int, FailureKind] = {
    status: kind for kind, status in _HTTP_STATUS_BY_KIND.items()
}

_DEFAULT_MESSAGE_BY_KIND: dict[FailureKind, str] = {
    FailureKind.VALIDATION_FAILED: "Validation failed.",
    FailureKind.UNAUTHORIZED: "Authentication required.",
    FailureKind.FORBIDDEN: "Access forbidden.",
    FailureKind.NOT_FOUND: "Resource not found.",
    FailureKind.CONFLICT: "Resource conflict.",
    FailureKind.RATE_LIMITED: "Too many requests.",
    FailureKind.SERVICE_UNAVAILABLE: "Service unavailable.",
    FailureKind.INTERNAL: _GENERIC_INTERNAL_MESSAGE,
}


def http_status_for(kind: FailureKind) -> int:
    """Map a failure kind to its HTTP status (the single mapping)."""
    return _HTTP_STATUS_BY_KIND[kind]


def kind_for_http_status(status: int) -> FailureKind:
    """Map an HTTP status to the closest failure kind.

    Statuses the taxonomy names map exactly; unnamed 4xx statuses take the
    ``not_found`` bucket (closest client-error kind — e.g. 405 method not
    allowed) and unnamed 5xx statuses take ``internal``. The response keeps
    the truthful status either way.
    """
    exact = _KIND_BY_HTTP_STATUS.get(status)
    if exact is not None:
        return exact
    return FailureKind.NOT_FOUND if status < 500 else FailureKind.INTERNAL


class AppError(Exception):
    """Typed application error: kind + message + optional details/headers.

    Domain and data layers raise this (or subclasses later phases add); the
    exception handlers translate it into the envelope. ``details`` carries
    structured context for clients (e.g. which fields failed validation).
    ``headers`` lets a failure carry the response headers its STATUS
    semantically requires — the 429 rate-limit rejection owns a
    ``Retry-After``, and the taxonomy is the one place it can be attached.
    """

    def __init__(
        self,
        kind: FailureKind,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.kind = kind
        self.message = message
        self.details = details
        self.headers = headers
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.kind.value}] {self.message}"


class ErrorBody(CamelModel):
    """The ``error`` object of the envelope; wire keys are camelCase."""

    code: str
    """Machine-readable failure kind (e.g. ``not_found``)."""

    message: str
    """Human-readable, client-safe message."""

    request_id: str
    """The request id from the request-context middleware."""

    details: dict[str, Any] | list[dict[str, Any]] | None = None
    """Optional structured context; omitted from the wire when absent."""


class ErrorResponse(CamelModel):
    """The whole error envelope: ``{"error": {...}}``."""

    error: ErrorBody


def _build_error_response(
    request: Request,
    status: int,
    kind: FailureKind,
    message: str,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the envelope JSONResponse, stamping the x-request-id header.

    The header is set here (not only in the middleware) because responses
    produced by the outermost ServerErrorMiddleware never pass back through
    the middleware stack.
    """
    request_id = resolve_request_id(request)
    body = ErrorResponse(
        error=ErrorBody(code=kind.value, message=message, request_id=request_id, details=details)
    )
    headers = {"x-request-id": request_id}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        status_code=status,
        content=body.model_dump(mode="json", by_alias=True, exclude_none=True),
        headers=headers,
    )


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """AppError → its mapped status + envelope; logged with the request id."""
    logger.warning(
        "app_error",
        request_id=resolve_request_id(request),
        kind=exc.kind.value,
        message=exc.message,
    )
    return _build_error_response(
        request,
        http_status_for(exc.kind),
        exc.kind,
        exc.message,
        exc.details,
        extra_headers=exc.headers,
    )


async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """FastAPI body/path/query validation → 422 validation_failed envelope.

    Pydantic's raw errors carry url/ctx noise; clients get the normalized
    ``{loc, msg, type}`` triples only.
    """
    details = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]} for err in exc.errors()
    ]
    logger.info(
        "request_validation_failed",
        request_id=resolve_request_id(request),
        detail_count=len(details),
    )
    return _build_error_response(
        request,
        422,
        FailureKind.VALIDATION_FAILED,
        "Request validation failed.",
        details,
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Starlette HTTPException → envelope with the closest kind, truthful status."""
    kind = kind_for_http_status(exc.status_code)
    message = str(exc.detail) if exc.detail else _DEFAULT_MESSAGE_BY_KIND[kind]
    logger.warning(
        "http_exception",
        request_id=resolve_request_id(request),
        status_code=exc.status_code,
        kind=kind.value,
    )
    extra = {key: str(value) for key, value in (exc.headers or {}).items()}
    return _build_error_response(request, exc.status_code, kind, message, extra_headers=extra)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: 500 internal, generic message, traceback logged.

    Registered for bare ``Exception``, so Starlette routes it to the
    outermost ServerErrorMiddleware — the response never re-enters the
    middleware stack, hence the header is stamped here.
    """
    request_id = resolve_request_id(request)
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        error=type(exc).__name__,
        exc_info=exc,
    )
    return _build_error_response(request, 500, FailureKind.INTERNAL, _GENERIC_INTERNAL_MESSAGE)


def register_exception_handlers(app: FastAPI) -> None:
    """Wire the taxonomy's handlers onto one app (called once per app)."""
    # Handlers narrow `exc` below the Exception the base signature declares
    # (each is registered for exactly that narrower class) — hence the ignores.
    add = app.add_exception_handler
    add(AppError, handle_app_error)  # type: ignore[arg-type]
    add(RequestValidationError, handle_request_validation_error)  # type: ignore[arg-type]
    add(HTTPException, handle_http_exception)  # type: ignore[arg-type]
    add(Exception, handle_unexpected_error)
