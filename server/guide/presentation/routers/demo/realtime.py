"""The realtime demo panels: topic 28's live labs (area ``realtime``).

Thin routers (family invariant): the ticker panel and its firehose stats
shape what the ticker service already knows; the chat panel shapes the
rooms, ceilings, and close-code table the chat service + manager own. The
LIVE endpoints themselves are not here — the SSE stream and the websocket
live one level up at ``/api/realtime`` (``routers/realtime.py``), because
they are the real substrate, not demo payloads.

Endpoint map (prefix ``/api/demo/realtime``):

- ``GET /ticker``        — the stream's front page (policy, stats, tour)
- ``GET /ticker/stats``  — the firehose odometer (polled while streaming)
- ``GET /chat``          — rooms, roster, transcript, ceiling facts
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Query, Request

from guide.core.errors import AppError, FailureKind
from guide.domain.demos.realtime_chat import ChatPanel, build_chat_panel
from guide.domain.demos.realtime_ticker import (
    TickerPanel,
    TickerStatsPanel,
    build_ticker_panel,
    build_ticker_stats,
)
from guide.domain.realtime.chat import ChatRoomService, valid_room
from guide.domain.realtime.ticker import TickerService

router = APIRouter(prefix="/api/demo/realtime", tags=["demo:realtime"])

TICKER_PANEL_PATH: Final = "/ticker"
TICKER_STATS_PATH: Final = "/ticker/stats"
CHAT_PANEL_PATH: Final = "/chat"
"""The router's paths (prefix-relative) — the terminal companion names them."""


def get_ticker_service(request: Request) -> TickerService:
    """FastAPI dependency: the shared ticker service (wired in create_app)."""
    service = request.app.state.ticker_service
    if not isinstance(service, TickerService):
        raise AppError(FailureKind.INTERNAL, "ticker service not wired on app.state")
    return service


def get_chat_service(request: Request) -> ChatRoomService:
    """FastAPI dependency: the chat room service (wired in create_app)."""
    service = request.app.state.chat_service
    if not isinstance(service, ChatRoomService):
        raise AppError(FailureKind.INTERNAL, "chat service not wired on app.state")
    return service


TickerDep = Annotated[TickerService, Depends(get_ticker_service)]
ChatDep = Annotated[ChatRoomService, Depends(get_chat_service)]


@router.get(TICKER_PANEL_PATH, response_model=TickerPanel)
async def read_ticker_panel(service: TickerDep) -> TickerPanel:
    """The stream's front page: policy, live stats, endpoint tour, honesty."""
    return build_ticker_panel(service)


@router.get(TICKER_STATS_PATH, response_model=TickerStatsPanel)
async def read_ticker_stats(service: TickerDep) -> TickerStatsPanel:
    """The firehose odometer — the streaming client polls this while live."""
    return build_ticker_stats(service)


@router.get(CHAT_PANEL_PATH, response_model=ChatPanel)
async def read_chat_panel(
    service: ChatDep,
    room: Annotated[str | None, Query(min_length=1, max_length=24)] = None,
) -> ChatPanel:
    """The rooms as they stand: rosters, transcript, ceilings, close codes.

    ``room`` pins whose transcript leads (the demo client sends the room
    it is about to join); an invalid room id falls back to the most
    recently active one — the panel stays a VIEW, never a validator.
    """
    selected = room if room is not None and valid_room(room) else None
    return build_chat_panel(service, room=selected)
