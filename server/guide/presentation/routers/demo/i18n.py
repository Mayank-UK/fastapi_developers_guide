"""The i18n negotiator demo: topic 27's live lab (area ``i18n``).

Thin routers (family invariant): every decision — parsing, matching,
fallback chains, CLDR formatting, zone conversion — lives in the domain;
this file reads ONE header, calls the service twice (negotiate, then
render in the negotiated locale), and maps the result onto the response.
The teaching point rides in the header's very ordinariness: the browser
sends ``Accept-Language`` on EVERY request, so the negotiate endpoint
reads the real header rather than a query parameter — presets and free
input on the panel are just different values for that one real header.

Endpoint map (prefix ``/api/demo/i18n``):

- ``GET /``           — the panel: policy, catalog table, tour, honesty notes
- ``GET /negotiate``  — one Accept-Language header, fully answered
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Header, Request

from guide.core.errors import AppError, FailureKind
from guide.domain.demos.i18n_negotiator import (
    I18nPanel,
    NegotiatorRound,
    build_i18n_panel,
    build_negotiator_round,
)
from guide.domain.i18n.service import I18nService

router = APIRouter(prefix="/api/demo/i18n", tags=["demo:i18n"])

PANEL_PATH: Final = ""
NEGOTIATE_ROUTE: Final = "/negotiate"
"""The router's paths (prefix-relative) — the terminal companion names them."""


def get_i18n_service(request: Request) -> I18nService:
    """FastAPI dependency: the i18n service (wired in create_app)."""
    service = request.app.state.i18n_service
    if not isinstance(service, I18nService):
        raise AppError(FailureKind.INTERNAL, "i18n service not wired on app.state")
    return service


ServiceDep = Annotated[I18nService, Depends(get_i18n_service)]


@router.get(PANEL_PATH, response_model=I18nPanel)
async def read_i18n_panel(service: ServiceDep) -> I18nPanel:
    """The negotiator panel: policy, catalog table, tour, honesty notes."""
    return build_i18n_panel(service)


@router.get(NEGOTIATE_ROUTE, response_model=NegotiatorRound)
async def read_negotiation(
    service: ServiceDep,
    accept_language: Annotated[str | None, Header()] = None,
) -> NegotiatorRound:
    """Answer one Accept-Language header: ranked parse, locale, every layer.

    A malformed header is NOT an error — the engine skips bad elements and
    may fall back to the default locale, with the fallback visible in the
    payload (``fellBackToDefault``), which is the topic's standing lesson
    about hostile input on a preference header.
    """
    negotiation = service.negotiate(accept_language)
    rendering = service.render(negotiation.selected)
    return build_negotiator_round(service, negotiation, rendering)
