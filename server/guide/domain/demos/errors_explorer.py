"""The errors explorer payload: the eight kinds, their real triggers, their logs.

``build_errors_panel`` shapes the panel topic 30's ``errors:explorer`` serves
INLINE in the failure-injection section: one row per ``FailureKind`` with the
status and default message straight from the taxonomy's own tables (the
private ``_DEFAULT_MESSAGE_BY_KIND`` import is deliberate — the alternative
is restating eight strings here, which is exactly the drift the single-source
rule exists to prevent), each row carrying the REAL trigger that fires the
kind against existing endpoints and the log event its handler writes. Two
kinds carry recipes instead of buttons: their raise sites are real code the
topic quotes, but their live triggers need conditions the running stack
honestly does not have — conflict needs the arq adapter to send a duplicate
job id it never sends, service_unavailable needs an optional store down —
and the panel says so in plain words rather than faking a trigger.

``build_probe_row`` shapes the healthy answer of the probe endpoint; the
INJECTED halves never reach a builder — the probe raises a genuine unhandled
``RuntimeError`` (the outermost handler answers the generic 500 envelope) or
sleeps out the latency injection, which is exactly the behavior the demo
teaches.
"""

from typing import Final, Literal

from guide.core.errors import (
    _DEFAULT_MESSAGE_BY_KIND,
    _HTTP_STATUS_BY_KIND,
    FailureKind,
)
from guide.core.scenario import ScenarioState
from guide.core.serialization import CamelModel

SCENARIO_PATCH_PATH: Final = "/api/demo/scenario"
"""The scenario store's real endpoints — the panel's scenario sub-panel."""

MINT_PATH: Final = "/api/demo/auth/jwt/mint"
"""Topic 23's real token mint — the forbidden trigger's prep step."""

GRACE_POST: Final = "/api/demo/authz/posts/designing-urls-people-can-read"
"""The authz-guarded edit (topic 24) — grace's own post, the demo's target."""

BURN_PATH: Final = "/api/demo/security/rate-limit/burn"
"""Topic 25's burnable endpoint — the rate_limited trigger."""

MISSING_POST_PATH: Final = "/api/posts/no-such-post"
"""The posts resource — the not_found trigger."""

PROBE_PATH: Final = "/api/demo/errors/probe"
"""The scenario-honoring probe (this demo area's own endpoint)."""


class TriggerSpec(CamelModel):
    """How to fire one kind for real — or why only a recipe exists."""

    mode: Literal["live", "recipe"]
    method: str
    path: str
    body: str | None = None
    prep: str | None = None
    note: str


class ErrorKindRow(CamelModel):
    """One failure kind: status, default message, raiser, log, trigger."""

    kind: str
    http_status: int
    default_message: str
    raised_by: str
    logged_as: str
    trigger: TriggerSpec


class ScenarioPanelRow(CamelModel):
    """The scenario sub-panel: the real GET/PATCH endpoints and the modes."""

    get_endpoint: str
    patch_endpoint: str
    modes: tuple[str, ...]
    note: str


class ProbePanelRow(CamelModel):
    """The probe: the endpoint, the injection modes, what each answers."""

    probe_endpoint: str
    latency_seconds: float
    healthy_note: str
    injected_note: str
    latency_note: str


class ErrorsPanel(CamelModel):
    """Wire shape of ``GET /api/demo/errors`` — the explorer's contract."""

    kinds: list[ErrorKindRow]
    envelope_note: str
    scenario: ScenarioPanelRow
    probe: ProbePanelRow
    reasoning: str


class ProbeRow(CamelModel):
    """Wire shape of ``GET /api/demo/errors/probe`` on a healthy scenario."""

    status: str
    inject_failure: str
    detail: str


_KIND_CONTEXT: Final[dict[FailureKind, tuple[str, str, TriggerSpec]]] = {
    FailureKind.VALIDATION_FAILED: (
        "FastAPI's RequestValidationError — pydantic rejects a body/path/query "
        "before any handler runs (guide/core/errors.py renders it)",
        "request_validation_failed · info — request id + how many detail triples",
        TriggerSpec(
            mode="live",
            method="PATCH",
            path=SCENARIO_PATCH_PATH,
            body='{"injectFailure": "bogus"}',
            note=(
                "an enum value the scenario model refuses — FastAPI answers the "
                "422 envelope with one {loc, msg, type} triple per problem"
            ),
        ),
    ),
    FailureKind.UNAUTHORIZED: (
        "the auth guards — resolve_principal without a valid credential "
        "(guide/presentation/dependencies/authz.py)",
        "app_error · warning — kind + message + request id",
        TriggerSpec(
            mode="live",
            method="PUT",
            path=GRACE_POST,
            note=(
                "the authz-guarded edit with no credential headers at all — the "
                "401 envelope answers before the handler body runs"
            ),
        ),
    ),
    FailureKind.FORBIDDEN: (
        "the authz guards — require_owner_or / require_permission deny with the "
        "engine's reason in details (guide/presentation/dependencies/authz.py)",
        "app_error · warning — kind + message + request id",
        TriggerSpec(
            mode="live",
            method="PUT",
            path=GRACE_POST,
            prep=f"mint alan's token first: POST {MINT_PATH} "
            '{"username": "alan", "scopes": ["*"]}',
            note=(
                "alan is a viewer — the token is valid (401 never fires) but no "
                "role grants the write, so the 403 envelope carries the deny reason"
            ),
        ),
    ),
    FailureKind.NOT_FOUND: (
        "use cases and thin routers raise it directly — e.g. GetPostUseCase "
        "and the content router's unknown-topic branch",
        "app_error · warning — kind + message + request id",
        TriggerSpec(
            mode="live",
            method="GET",
            path=MISSING_POST_PATH,
            note="a well-formed id that names nothing — the plain 404 envelope",
        ),
    ),
    FailureKind.CONFLICT: (
        "the arq adapter's duplicate-refusal guard — enqueue translates arq's "
        "'job id already queued' refusal (guide/data/jobs/arq_jobs.py)",
        "app_error · warning — kind + message + request id",
        TriggerSpec(
            mode="recipe",
            method="POST",
            path="/api/demo/jobs/enqueue",
            note=(
                "no live trigger BY DESIGN: the adapter never sends a _job_id of "
                "its own, so arq never refuses one — the guard exists for the day "
                "something changes that, and this row exists so conflict is not a "
                "kind you have never seen"
            ),
        ),
    ),
    FailureKind.RATE_LIMITED: (
        "the rate-limit dependency — the exhausted verdict raises with "
        "Retry-After riding AppError.headers "
        "(guide/presentation/dependencies/rate_limit.py)",
        "app_error · warning — kind + message + request id",
        TriggerSpec(
            mode="live",
            method="POST",
            path=BURN_PATH,
            prep="fire it six times — five drain the budget, the sixth is the 429",
            note=(
                "the real sliding-window burner (topic 25): the 429 envelope "
                "carries Retry-After and the budget self-heals after the window"
            ),
        ),
    ),
    FailureKind.SERVICE_UNAVAILABLE: (
        "the optional-store adapters' degradation guards — e.g. the redis "
        "playground refuses to serve stale facts when Redis is unreachable "
        "(guide/data/redis/playground.py)",
        "app_error · warning — the adapter logs its own unavailable event first",
        TriggerSpec(
            mode="recipe",
            method="GET",
            path="/api/demo/redis",
            prep=(
                "docker stop fastapi_developers_guide_redis_dev — and start it "
                "again after"
            ),
            note=(
                "needs the optional store down, which the running stack honestly "
                "is not: stop Redis, call the playground, watch ONLY that demo "
                "degrade while the app keeps serving everything else"
            ),
        ),
    ),
    FailureKind.INTERNAL: (
        "nothing raises internal on purpose — it is what the last-resort "
        "handler answers for any exception nothing else caught",
        "unhandled_exception · error — traceback via exc_info + request id",
        TriggerSpec(
            mode="live",
            method="GET",
            path=PROBE_PATH,
            prep=f"PATCH {SCENARIO_PATCH_PATH} "
            '{"injectFailure": "error"} — then reset it to "none" after',
            note=(
                "the scenario's failure injection, honored by the probe below: "
                "the probe raises a genuine unhandled RuntimeError and the "
                "outermost handler answers the generic 500 envelope — the client "
                "sees no traceback, the log sees all of it"
            ),
        ),
    ),
}
"""Raised-by, logged-as, and the trigger for each kind — the panel's one table."""


def build_errors_panel() -> ErrorsPanel:
    """Shape the panel (pure) from the taxonomy's own tables."""
    kinds = [
        ErrorKindRow(
            kind=kind.value,
            http_status=_HTTP_STATUS_BY_KIND[kind],
            default_message=_DEFAULT_MESSAGE_BY_KIND[kind],
            raised_by=raised_by,
            logged_as=logged_as,
            trigger=trigger,
        )
        for kind, (raised_by, logged_as, trigger) in _KIND_CONTEXT.items()
    ]
    return ErrorsPanel(
        kinds=kinds,
        envelope_note=(
            "every failure this server produces answers the SAME envelope — "
            '{"error": {code, message, requestId, details?}} — and stamps the '
            "x-request-id header on the response, so a client writes its error "
            "handling exactly once and a human can grep the request id in the "
            "server log to find the exact lines that failed"
        ),
        scenario=ScenarioPanelRow(
            get_endpoint=SCENARIO_PATCH_PATH,
            patch_endpoint=SCENARIO_PATCH_PATH,
            modes=("none", "error", "latency"),
            note=(
                "the runtime toggle every demo reads — PATCH it, probe it, PATCH "
                "it back; invalid values answer the 422 envelope (which is "
                "itself the validation trigger above)"
            ),
        ),
        probe=ProbePanelRow(
            probe_endpoint=PROBE_PATH,
            latency_seconds=1.5,
            healthy_note=(
                'with injectFailure=none the probe answers 200 {"status": '
                '"healthy"} — the round trip is inject, watch the 500, reset, '
                "watch the 200"
            ),
            injected_note=(
                "with injectFailure=error the probe raises an unhandled "
                "RuntimeError: the outermost handler logs the traceback with the "
                "request id and answers the generic 500 envelope"
            ),
            latency_note=(
                "with injectFailure=latency the probe sleeps out the injection "
                "before answering 200 — latency is a failure mode too, just one "
                "the stopwatch catches instead of the taxonomy"
            ),
        ),
        reasoning=(
            "Eight kinds, one envelope, zero exceptions to either: each row "
            "fires its kind against the real machinery this guide built in "
            "earlier topics, and the two recipe rows say plainly why their "
            "triggers need conditions the running stack does not have — the "
            "panel never fakes an error it did not really produce."
        ),
    )


def build_probe_row(state: ScenarioState) -> ProbeRow:
    """Shape the probe's healthy answer for the current scenario mode."""
    return ProbeRow(
        status="healthy",
        inject_failure=state.inject_failure,
        detail=(
            "probe answered normally — PATCH /api/demo/scenario to "
            '{"injectFailure": "error"} and probe again to watch the 500 '
            "envelope arrive without a traceback in sight"
        ),
    )
