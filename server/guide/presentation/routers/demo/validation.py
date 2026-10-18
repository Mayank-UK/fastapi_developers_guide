"""Validation arena demo API: the roster of real models + the arena itself.

Thin routers (family invariant). ``GET /arena/roster`` serves the three
contenders and their field rules; ``POST /arena`` takes an ``ArenaRequest``
— a Literal model choice plus raw candidate values — and answers with the
per-field verdicts of the REAL pydantic validation the chosen model runs
over the candidates, including the exact ``{loc, msg, type}`` triples the
422 ``validation_failed`` envelope would carry. The edge validates this
request body the same way it validates anything else: an unknown model key
or a non-object ``candidates`` value is FastAPI's own 422 before the
builder runs — itself part of the lesson.
"""

from fastapi import APIRouter

from guide.domain.demos.validation_arena import (
    ArenaRequest,
    ArenaRosterPayload,
    ArenaVerdictPayload,
    build_arena_roster,
    build_arena_verdict,
)

router = APIRouter(prefix="/api/demo/validation", tags=["demo:validation"])


@router.get("/arena/roster", response_model=ArenaRosterPayload)
def read_arena_roster() -> ArenaRosterPayload:
    """Serve the roster: the real models, their fields, their rules."""
    return build_arena_roster()


@router.post(
    "/arena", response_model=ArenaVerdictPayload, response_model_exclude_none=True
)
def run_arena(request: ArenaRequest) -> ArenaVerdictPayload:
    """Judge one round: the chosen model's real validation over the candidates."""
    return build_arena_verdict(request)
