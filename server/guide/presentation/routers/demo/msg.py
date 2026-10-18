"""Messaging demos: topic 22's stream lab + outbox lab (area ``msg``).

Thin routers (family invariant). The stream lab (``GET /stream`` roster;
``POST /stream/produce`` XADD; ``POST /stream/consume`` XREADGROUP as
the healthy or poison consumer; ``GET /stream/pending`` XPENDING;
``POST /stream/reclaim`` XAUTOCLAIM) runs entirely against Redis through
the ``StreamLabService`` the composition root wires. The outbox lab
(``GET /outbox`` roster; ``POST /outbox/posts`` the ONE-transaction
dual write; ``POST /outbox/relay`` poll → publish → mark, with the
optional crash window; ``POST /outbox/consume`` the idempotent walk)
spans PostgreSQL and Redis through ``OutboxRelayService``, and its
endpoints ensure the PG seed first (the idempotent dependency the
database demos share). With Redis or PostgreSQL down, the affected
routes degrade to the service_unavailable envelope.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from guide.core.errors import AppError, FailureKind
from guide.domain.db.ports import GuideRepository
from guide.domain.demos.msg_outbox import OutboxPanelPayload, build_outbox_panel_payload
from guide.domain.demos.msg_stream import StreamPanelPayload, build_stream_panel_payload
from guide.domain.messaging.outbox_service import OutboxRelayService
from guide.domain.messaging.ports import (
    ConsumeRequest,
    ConsumeRow,
    OutboxConsumeRow,
    OutboxPostDraft,
    OutboxWriteRow,
    PendingListRow,
    ProduceRequest,
    ProduceRow,
    ReclaimRequest,
    ReclaimRow,
    RelayRequest,
    RelayRow,
)
from guide.domain.messaging.stream_service import StreamLabService
from guide.presentation.routers.demo.db import get_seeded_repository

router = APIRouter(prefix="/api/demo/msg", tags=["demo:msg"])

STREAM_ROSTER_PATH = "/stream"
PRODUCE_PATH = "/stream/produce"
CONSUME_PATH = "/stream/consume"
PENDING_PATH = "/stream/pending"
RECLAIM_PATH = "/stream/reclaim"
OUTBOX_ROSTER_PATH = "/outbox"
POSTS_PATH = "/outbox/posts"
RELAY_PATH = "/outbox/relay"
CONSUME_OUTBOX_PATH = "/outbox/consume"
"""The labs' paths — the terminal companion's tour names them."""


def get_stream_lab(request: Request) -> StreamLabService:
    """FastAPI dependency: the stream lab engine (wired in create_app)."""
    service = request.app.state.stream_lab
    if not isinstance(service, StreamLabService):
        raise AppError(FailureKind.INTERNAL, "Stream lab service not wired on app.state")
    return service


def get_outbox_service(request: Request) -> OutboxRelayService:
    """FastAPI dependency: the outbox relay engine (wired in create_app)."""
    service = request.app.state.outbox_service
    if not isinstance(service, OutboxRelayService):
        raise AppError(FailureKind.INTERNAL, "Outbox service not wired on app.state")
    return service


StreamLabDep = Annotated[StreamLabService, Depends(get_stream_lab)]
OutboxServiceDep = Annotated[OutboxRelayService, Depends(get_outbox_service)]
SeededDep = Annotated[GuideRepository, Depends(get_seeded_repository)]
"""The outbox lab's PG precondition: the seed exists (idempotent check)."""


@router.get(STREAM_ROSTER_PATH, response_model=StreamPanelPayload)
async def read_stream_panel(service: StreamLabDep) -> StreamPanelPayload:
    """Serve the stream lab roster: log in order, length, pending count, buttons."""
    panel = await service.panel()
    return build_stream_panel_payload(
        panel,
        produce_endpoint=f"{router.prefix}{PRODUCE_PATH}",
        consume_endpoint=f"{router.prefix}{CONSUME_PATH}",
        pending_endpoint=f"{router.prefix}{PENDING_PATH}",
        reclaim_endpoint=f"{router.prefix}{RECLAIM_PATH}",
    )


@router.post(PRODUCE_PATH, response_model=ProduceRow)
async def produce_entry(service: StreamLabDep, request: ProduceRequest) -> ProduceRow:
    """The produce button: mint an event id, XADD the note."""
    return await service.produce(request)


@router.post(CONSUME_PATH, response_model=ConsumeRow)
async def consume_entries(service: StreamLabDep, request: ConsumeRequest) -> ConsumeRow:
    """The consume button: read as the chosen persona; healthy acks, poison doesn't."""
    return await service.consume(request)


@router.get(PENDING_PATH, response_model=PendingListRow)
async def read_pending(service: StreamLabDep) -> PendingListRow:
    """The pending list: delivered-but-unacknowledged entries, owners, idle time."""
    return await service.pending()


@router.post(RECLAIM_PATH, response_model=ReclaimRow)
async def reclaim_stale(service: StreamLabDep, request: ReclaimRequest) -> ReclaimRow:
    """The reclaim button: XAUTOCLAIM stale pending entries, finish the work."""
    return await service.reclaim(request)


@router.get(OUTBOX_ROSTER_PATH, response_model=OutboxPanelPayload)
async def read_outbox_panel(service: OutboxServiceDep, _seeded: SeededDep) -> OutboxPanelPayload:
    """Serve the outbox roster: table counts, recent rows, stream, counters."""
    panel = await service.panel()
    return build_outbox_panel_payload(
        panel,
        posts_endpoint=f"{router.prefix}{POSTS_PATH}",
        relay_endpoint=f"{router.prefix}{RELAY_PATH}",
        consume_endpoint=f"{router.prefix}{CONSUME_OUTBOX_PATH}",
    )


@router.post(POSTS_PATH, response_model=OutboxWriteRow)
async def create_post_with_event(
    service: OutboxServiceDep, _seeded: SeededDep, draft: OutboxPostDraft
) -> OutboxWriteRow:
    """The create button: post + outbox event, ONE transaction, both or neither."""
    return await service.create_with_event(draft)


@router.post(RELAY_PATH, response_model=RelayRow)
async def run_relay_cycle(
    service: OutboxServiceDep, _seeded: SeededDep, request: RelayRequest
) -> RelayRow:
    """The relay button: poll unpublished, publish each, mark — or die before marking."""
    return await service.relay(request)


@router.post(CONSUME_OUTBOX_PATH, response_model=OutboxConsumeRow)
async def consume_outbox_stream(service: OutboxServiceDep) -> OutboxConsumeRow:
    """The consume button: the idempotent walk over the outbox stream."""
    return await service.consume()
