"""API demos: the posts workbench, the docs hub, the GraphQL playground, webhooks, gRPC.

Thin routers (family invariant). ``GET /workbench`` serves the substrate's
live facets (authors, tags, statuses, sorts) derived from the SAME use
case the real list route runs; ``POST /workbench`` takes a
``WorkbenchRequest`` — method + path template + query/id/body — resolves
it against the real route table's shape, runs it through the SAME
``PostUseCases`` bundle ``/api/posts`` resolves, and answers with the
layer-by-layer outcome the pure builders assemble. ``GET /docs-link``
(topic 12's demo) introspects the RUNNING app's generated documentation —
the same schema ``/openapi.json`` serves, via ``app.openapi()`` — and
hands it to the pure builder that shapes the hub. ``GET
/graphql-playground`` (topic 13's demo) packages the REAL GraphQL
schema's SDL (``schema.as_str()``, from the mounted router's own schema
object) with a curated query tour. ``GET/POST /webhook-simulator``
(topic 14's demo) serve the delivery simulator — scenario, event, and
every attempt with its real HMAC signature — while
``POST /webhooks/receive`` is a REAL receive endpoint: it verifies a
signed delivery over the raw request bytes with the domain verifier and
answers 202 FAST, or the 401 envelope on a bad signature.
``GET/POST /grpc-console`` (topic 15's demo) drive the REAL in-process
gRPC satellite through the domain port: the roster names the bound
address and the contract's four methods; POST performs one real
``grpc.aio`` round (method + arguments + optional deadline) and the pure
builder shapes the adapter's outcome — messages, status code, elapsed
time. The routers only orchestrate: one call per operation, one builder
per result; every fact in every payload comes from that real run.
"""

import json
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from guide.core.errors import AppError, FailureKind
from guide.core.request_context import current_request_id
from guide.core.result import Err
from guide.domain.demos.docs_link import DocsLinkPayload, build_docs_link_payload
from guide.domain.demos.graphql_playground import (
    GraphqlPlaygroundPayload,
    build_graphql_playground_payload,
)
from guide.domain.demos.grpc_console import (
    GrpcConsoleRoster,
    GrpcConsoleRound,
    build_grpc_console_roster,
    build_grpc_console_round,
)
from guide.domain.demos.posts_workbench import (
    WorkbenchPayload,
    WorkbenchRequest,
    WorkbenchRosterPayload,
    build_create_outcome,
    build_get_outcome,
    build_list_outcome,
    build_method_not_allowed,
    build_replace_outcome,
    build_workbench_roster,
    workbench_operation,
)
from guide.domain.demos.webhook_simulator import (
    WebhookReceiptPayload,
    WebhookSimulatorPayload,
    WebhookSimulatorRequest,
    WebhookSimulatorRoster,
    build_webhook_simulator_payload,
    build_webhook_simulator_roster,
)
from guide.domain.grpc.entities import STREAM_PAUSE_MS, GrpcConsoleRequest
from guide.domain.grpc.ports import GrpcConsole
from guide.domain.posts.entities import PostCreate, PostListQuery
from guide.domain.webhooks.signing import (
    DEMO_SHARED_SECRET,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    verify_payload,
)
from guide.presentation.routers.graphql import GRAPHQL_PATH
from guide.presentation.routers.graphql import schema as graphql_schema
from guide.presentation.routers.posts import PostUseCasesDep

router = APIRouter(prefix="/api/demo/api", tags=["demo:api"])

WEBHOOK_RECEIVE_PATH = "/webhooks/receive"
"""The real receive endpoint's path under this router — the tour and roster name it."""


def get_grpc_console(request: Request) -> GrpcConsole:
    """FastAPI dependency: the gRPC console (wired in create_app)."""
    console = request.app.state.grpc_console
    if not isinstance(console, GrpcConsole):
        raise AppError(FailureKind.INTERNAL, "gRPC console not wired on app.state")
    return console


GrpcConsoleDep = Annotated[GrpcConsole, Depends(get_grpc_console)]


def _required_post_id(request: WorkbenchRequest) -> str:
    """The post_id the request model guarantees for item-template rounds."""
    if request.post_id is None:
        raise AppError(FailureKind.INTERNAL, "Workbench post_id missing after validation")
    return request.post_id


def _required_body(request: WorkbenchRequest) -> PostCreate:
    """The body the request model guarantees for POST/PUT rounds."""
    if request.body is None:
        raise AppError(FailureKind.INTERNAL, "Workbench body missing after validation")
    return request.body


@router.get("/workbench", response_model=WorkbenchRosterPayload)
def read_workbench(use_cases: PostUseCasesDep) -> WorkbenchRosterPayload:
    """Serve the substrate's live facets through the real list use case."""
    result = use_cases.list_posts.execute(PostListQuery(limit=100, sort="oldest"))
    if isinstance(result, Err):
        raise result.failure
    return build_workbench_roster(result.value)


@router.get("/docs-link", response_model=DocsLinkPayload, response_model_exclude_none=True)
def read_docs_link(request: Request) -> DocsLinkPayload:
    """Introspect the running app's generated docs: facts, links, one schema slice."""
    app = request.app
    return build_docs_link_payload(
        title=app.title,
        version=app.version,
        docs_url=app.docs_url,
        redoc_url=app.redoc_url,
        openapi_url=app.openapi_url,
        schema=app.openapi(),
    )


@router.get("/graphql-playground", response_model=GraphqlPlaygroundPayload)
def read_graphql_playground() -> GraphqlPlaygroundPayload:
    """Serve the GraphQL playground package: the live SDL + curated queries."""
    return build_graphql_playground_payload(
        endpoint=GRAPHQL_PATH,
        sdl=graphql_schema.as_str(),
    )


@router.post("/workbench", response_model=WorkbenchPayload, response_model_exclude_none=True)
def run_workbench(request: WorkbenchRequest, use_cases: PostUseCasesDep) -> WorkbenchPayload:
    """Run one picked request through the real posts pipeline."""
    operation = workbench_operation(request)
    request_id = current_request_id()
    if operation == "method-not-allowed":
        return build_method_not_allowed(request, request_id)
    if operation == "list":
        query = request.query if request.query is not None else PostListQuery()
        return build_list_outcome(request, use_cases.list_posts.execute(query), request_id)
    if operation == "get":
        post_id = _required_post_id(request)
        return build_get_outcome(request, use_cases.get_post.execute(post_id), request_id)
    if operation == "create":
        return build_create_outcome(
            request, use_cases.create_post.execute(_required_body(request)), request_id
        )
    # operation == "replace"
    post_id = _required_post_id(request)
    return build_replace_outcome(
        request, use_cases.replace_post.execute(post_id, _required_body(request)), request_id
    )


@router.get(
    "/webhook-simulator", response_model=WebhookSimulatorRoster, response_model_exclude_none=True
)
def read_webhook_simulator() -> WebhookSimulatorRoster:
    """Serve the simulator roster: scenarios, catalog, secret, schedule."""
    return build_webhook_simulator_roster(
        secret=DEMO_SHARED_SECRET,
        receive_endpoint=f"{router.prefix}{WEBHOOK_RECEIVE_PATH}",
    )


@router.post(
    "/webhook-simulator",
    response_model=WebhookSimulatorPayload,
    response_model_exclude_none=True,
)
def run_webhook_simulator(request: WebhookSimulatorRequest) -> WebhookSimulatorPayload:
    """Register a subscription + fire an event; walk the full simulated lifecycle."""
    return build_webhook_simulator_payload(
        subscription_id=f"sub_{uuid.uuid4().hex[:12]}",
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        fired_at=int(time.time()),
        event_type=request.event_type,
        scenario=request.scenario,
        note=request.note,
        secret=DEMO_SHARED_SECRET,
        receive_endpoint=f"{router.prefix}{WEBHOOK_RECEIVE_PATH}",
    )


def _signed_event_id(payload: str) -> str | None:
    """The event id from an already-signature-verified body, None if not JSON."""
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    event_id = parsed.get("id") if isinstance(parsed, dict) else None
    return event_id if isinstance(event_id, str) else None


@router.post(
    WEBHOOK_RECEIVE_PATH,
    status_code=202,
    response_model=WebhookReceiptPayload,
    response_model_exclude_none=True,
)
async def receive_webhook(request: Request) -> WebhookReceiptPayload:
    """Verify a REAL signed delivery and acknowledge fast (202 Accepted).

    The signature covers the exact bytes the sender put on the wire, so
    this reads the RAW body first and only then parses anything — and the
    answer is the thin receipt, not the processing: verify, acknowledge,
    let the work happen after the 202 is already on the wire. Every
    failure mode maps to the taxonomy's unauthorized envelope (401).
    """
    try:
        payload = (await request.body()).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AppError(
            FailureKind.UNAUTHORIZED, "Webhook body is not valid UTF-8."
        ) from exc
    timestamp_header = request.headers.get(TIMESTAMP_HEADER)
    signature_header = request.headers.get(SIGNATURE_HEADER)
    if timestamp_header is None or signature_header is None:
        raise AppError(
            FailureKind.UNAUTHORIZED,
            f"Webhook needs both {TIMESTAMP_HEADER} and {SIGNATURE_HEADER} headers.",
        )
    try:
        timestamp = int(timestamp_header)
    except ValueError as exc:
        raise AppError(
            FailureKind.UNAUTHORIZED,
            f"Webhook timestamp header {timestamp_header!r} is not an integer.",
        ) from exc
    now = int(time.time())
    result = verify_payload(
        secret=DEMO_SHARED_SECRET,
        timestamp=timestamp,
        signature=signature_header,
        payload=payload,
        now=now,
    )
    if isinstance(result, Err):
        raise result.failure
    receipt = result.value
    return WebhookReceiptPayload(
        event_id=_signed_event_id(payload),
        received_at=now,
        age_seconds=receipt.age_seconds,
        detail=(
            "Signature verified in constant time over the raw request bytes; "
            "accepted for processing — the 202 is already on the wire."
        ),
    )


@router.get("/grpc-console", response_model=GrpcConsoleRoster, response_model_exclude_none=True)
async def read_grpc_console(console: GrpcConsoleDep) -> GrpcConsoleRoster:
    """Serve the console roster: the live satellite, the contract, the methods."""
    address = await console.ensure_ready()
    return build_grpc_console_roster(
        server_address=address,
        stream_pause_ms=STREAM_PAUSE_MS,
    )


@router.post("/grpc-console", response_model=GrpcConsoleRound, response_model_exclude_none=True)
async def run_grpc_console(
    request: GrpcConsoleRequest, console: GrpcConsoleDep
) -> GrpcConsoleRound:
    """Perform one REAL gRPC round and shape the adapter's outcome."""
    outcome = await console.call(request)
    return build_grpc_console_round(request=request, outcome=outcome)
