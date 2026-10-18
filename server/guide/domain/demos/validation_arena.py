"""Validation arena: real roster models judged by real pydantic validation.

``GET /api/demo/validation/arena/roster`` and
``POST /api/demo/validation/arena`` serve these payloads. The arena's
point is that validation is not a
simulation: the caller names one of three REAL wire models this server
already validates elsewhere — ``NoteCreate`` (the notes playground's POST
body), ``LabSpecimen`` (the pyd lab's strict target, with a field validator
and a cross-field model validator), ``ScenarioPatch`` (the scenario toggle's
PATCH body, optional Literal enums) — and supplies candidate field values;
the builder runs the model's own ``model_validate`` over them and reports
per-field outcomes. Every accepted value, every coercion (original →
coerced), and every rejection's ``{loc, msg, type}`` triple comes from that
real run — the triples are exactly the ``details`` array the 422
``validation_failed`` envelope would carry for this body, ``body``-prefixed
the way FastAPI reports a request-model failure.

When a field's own validation passes but the MODEL refuses (another field
failed, or a cross-field rule fired), the row shows what the field's own
gate accepted and the verdict carries the refusal — pydantic collects every
field's errors, so nothing reported is speculation. The request model
itself is part of the lesson: an unknown model key or a non-object
``candidates`` value is refused by FastAPI's own 422 before this module
runs.

The builders are pure: plain data in, payload out — no I/O, no state.
"""

from typing import Annotated, Final, Literal, NamedTuple, get_args

from pydantic import Field, JsonValue, ValidationError
from pydantic_core import ErrorDetails

from guide.core.scenario import ScenarioPatch
from guide.core.serialization import CamelModel
from guide.domain.demos.pyd_lab import LabSpecimen
from guide.domain.demos.request_methods import NoteCreate

ArenaModelKey = Literal["note-create", "lab-specimen", "scenario-patch"]
"""The roster choice — a Literal so a bogus key is the edge's own 422."""


class ArenaRequest(CamelModel):
    """One arena round: name a roster model, supply candidate field values.

    ``candidates`` is deliberately raw JSON — whatever the caller believes
    the model's fields should carry, wire-spelled (camelCase), judged by the
    model itself. The Literal ``model`` is the boundary discipline in
    miniature: an unknown choice never reaches the builder.
    """

    model: ArenaModelKey
    candidates: dict[str, JsonValue]


class ArenaFieldSpec(CamelModel):
    """One field of a roster model: wire name, rule, required-ness."""

    name: str
    rule: str
    required: bool


class ArenaModelSummary(CamelModel):
    """One roster contender: the real class, where it lives, its fields."""

    key: ArenaModelKey
    model: str
    source: str
    description: str
    fields: list[ArenaFieldSpec]


class ReceivedValue(CamelModel):
    """What one candidate carried: type name + capped repr."""

    type: str
    repr: str


class AcceptedOutcome(CamelModel):
    """The field's own validation passed with this value unchanged."""

    status: Literal["accepted"]
    value: JsonValue
    value_type: str


class CoercedOutcome(CamelModel):
    """Lax validation changed the value (or its type) to satisfy the field."""

    status: Literal["coerced"]
    original: JsonValue
    original_type: str
    value: JsonValue
    value_type: str


class RejectedOutcome(CamelModel):
    """The model produced an error for this field — the envelope's triple."""

    status: Literal["rejected"]
    loc: list[str]
    msg: str
    type: str


class AbsentOutcome(CamelModel):
    """The candidates did not carry the field; the model has a default."""

    status: Literal["absent"]
    default: JsonValue | None = None


FieldOutcome = Annotated[
    AcceptedOutcome | CoercedOutcome | RejectedOutcome | AbsentOutcome,
    Field(discriminator="status"),
]
"""Discriminated on ``status`` — same pattern as the content model's blocks."""


class ArenaFieldRow(CamelModel):
    """One roster field judged against the candidates."""

    field: str
    rule: str
    required: bool
    received: ReceivedValue | None = None
    outcome: FieldOutcome


class ArenaError(CamelModel):
    """One rejection, normalized exactly like the 422 envelope's details."""

    loc: list[str]
    msg: str
    type: str


class ArenaRosterPayload(CamelModel):
    """Wire shape of GET /api/demo/validation/arena/roster."""

    models: list[ArenaModelSummary]
    reasoning: str


class ArenaVerdictPayload(CamelModel):
    """Wire shape of POST /api/demo/validation/arena (camelCase)."""

    model: ArenaModelSummary
    roster: list[ArenaModelSummary]
    rows: list[ArenaFieldRow]
    verdict: Literal["accepted", "rejected"]
    validated: dict[str, JsonValue] | None = None
    errors: list[ArenaError] | None = None
    extra_keys_ignored: list[str]
    reasoning: str


class _RosterEntry(NamedTuple):
    """Internal roster record: the real model class plus display metadata."""

    key: ArenaModelKey
    model_class: type[CamelModel]
    source: str
    description: str
    rules: dict[str, str]


_ROSTER: Final[tuple[_RosterEntry, ...]] = (
    _RosterEntry(
        key="note-create",
        model_class=NoteCreate,
        source="guide.domain.demos.request_methods",
        description=(
            "The notes playground's POST/PUT body (topic 09): a required "
            "title under Field length constraints, body and tags optional "
            "with defaults — the workaday request model, constraints "
            "declared where the contract is."
        ),
        rules={
            "title": "str — Field(min_length=1, max_length=80), required",
            "body": "str — optional, default ''",
            "tags": "list[str] — optional, default []",
        },
    ),
    _RosterEntry(
        key="lab-specimen",
        model_class=LabSpecimen,
        source="guide.domain.demos.pyd_lab",
        description=(
            "The pyd lab's strict target (topic 05): every field required, "
            "score bounds via Annotated Field(ge=1, le=100), handle "
            "canonicalized by a @field_validator, and a @model_validator "
            "cross-field rule — flag requires at least one tag."
        ),
        rules={
            "count": "int — numeric strings and whole floats coerce, required",
            "flag": 'bool — "true"/"on"/1/0 coerce, required',
            "tags": "list[str] — required (the model validator reads it)",
            "score": "int — Field(ge=1, le=100), required",
            "handle": "str — @field_validator canonicalizes, required",
        },
    ),
    _RosterEntry(
        key="scenario-patch",
        model_class=ScenarioPatch,
        source="guide.core.scenario",
        description=(
            "The scenario toggle's PATCH body: both fields optional Literal "
            "enums where missing keys mean unchanged — a vocabulary "
            "constraint instead of a numeric one, and the exact body "
            "PATCH /api/demo/scenario validates."
        ),
        rules={
            "dataMode": 'Literal["fake", "live"] — optional, default null',
            "injectFailure": 'Literal["none", "error", "latency"] — optional, default null',
        },
    ),
)
"""The arena's contenders — real models, judged by their own validation."""

_BY_KEY: Final[dict[str, _RosterEntry]] = {entry.key: entry for entry in _ROSTER}

_MAX_REPR: Final[int] = 80
"""Received reprs are capped so a hostile mega-payload cannot bloat the wire."""


def _short(value: object) -> str:
    """Cap a repr at ``_MAX_REPR`` characters, ellipsis-marked when longer."""
    text = repr(value)
    return text if len(text) <= _MAX_REPR else text[:_MAX_REPR] + "…"


def _json_safe(value: object) -> JsonValue:
    """Keep a pydantic default JSON-wire-ready; anything exotic reads as repr."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return repr(value)


def _wire_names(entry: _RosterEntry) -> dict[str, str]:
    """python field name → wire name (alias), in declaration order."""
    return {
        name: (info.alias if info.alias else name)
        for name, info in entry.model_class.model_fields.items()
    }


def _summary(entry: _RosterEntry) -> ArenaModelSummary:
    """Build the public summary from the real model's own FieldInfo."""
    fields = [
        ArenaFieldSpec(
            name=wire,
            rule=entry.rules[wire],
            required=entry.model_class.model_fields[python].is_required(),
        )
        for python, wire in _wire_names(entry).items()
        if wire in entry.rules
    ]
    unknown_rules = set(entry.rules) - {spec.name for spec in fields}
    if unknown_rules:
        raise ValueError(f"roster rules name unknown fields: {sorted(unknown_rules)}")
    return ArenaModelSummary(
        key=entry.key,
        model=entry.model_class.__name__,
        source=entry.source,
        description=entry.description,
        fields=fields,
    )


_ROSTER_SUMMARIES: Final[tuple[ArenaModelSummary, ...]] = tuple(
    _summary(entry) for entry in _ROSTER
)
"""Built at import so a mis-declared roster fails the process at startup."""


def _body_triples(errors: list[ErrorDetails]) -> list[ArenaError]:
    """Normalize raw pydantic errors to the envelope's ``body``-prefixed triples.

    Exactly what ``handle_request_validation_error`` does to a
    ``RequestValidationError`` — minus the url/ctx noise, with ``body``
    (the parameter location FastAPI reports for a request model) prepended.
    """
    return [
        ArenaError(
            loc=["body", *[str(part) for part in error["loc"]]],
            msg=error["msg"],
            type=error["type"],
        )
        for error in errors
    ]


def _field_error(errors: list[ErrorDetails], wire: str, python: str) -> ErrorDetails | None:
    """The first raw error whose loc names this field (wire or python name)."""
    for error in errors:
        if error["loc"] and str(error["loc"][0]) in (wire, python):
            return error
    return None


def _same_value(left: JsonValue, right: JsonValue) -> bool:
    """Equal AND identically typed — bool/int must not blur (1 is not True)."""
    return type(left) is type(right) and left == right


def _outcome_for(
    entry: _RosterEntry,
    wire: str,
    python: str,
    raw: JsonValue,
    instance_dump: dict[str, JsonValue] | None,
    errors: list[ErrorDetails],
) -> FieldOutcome:
    """Classify one present field: rejected / coerced / accepted, honestly.

    Truth order: the model's own error first (the envelope triple); then a
    value from a validated instance (real end-to-end coercion); then — only
    when the model refused elsewhere — a single-field probe through the same
    model, which yields an instance whenever the other fields can default;
    and finally the received value, reported as it was carried.
    """
    error = _field_error(errors, wire, python)
    if error is not None:
        return RejectedOutcome(
            status="rejected",
            loc=["body", *[str(part) for part in error["loc"]]],
            msg=error["msg"],
            type=error["type"],
        )
    dump = instance_dump
    if dump is None:
        try:
            probe = entry.model_class.model_validate({wire: raw})
        except ValidationError:
            probe = None
        if probe is not None:
            dump = probe.model_dump(mode="json", by_alias=True)
    value = dump.get(wire, raw) if dump is not None else raw
    if _same_value(value, raw):
        return AcceptedOutcome(status="accepted", value=raw, value_type=type(raw).__name__)
    return CoercedOutcome(
        status="coerced",
        original=raw,
        original_type=type(raw).__name__,
        value=value,
        value_type=type(value).__name__,
    )


def build_arena_verdict(request: ArenaRequest) -> ArenaVerdictPayload:
    """Judge one round: the real model's validation over the candidates (pure)."""
    entry = _BY_KEY[request.model]
    candidates = request.candidates
    try:
        instance: CamelModel | None = entry.model_class.model_validate(candidates)
        errors: list[ErrorDetails] = []
    except ValidationError as exc:
        instance = None
        errors = list(exc.errors())
    instance_dump: dict[str, JsonValue] | None = (
        instance.model_dump(mode="json", by_alias=True) if instance is not None else None
    )

    summary = next(item for item in _ROSTER_SUMMARIES if item.key == entry.key)
    wire_names = _wire_names(entry)
    known_keys = set(wire_names.values()) | set(wire_names)
    rows: list[ArenaFieldRow] = []
    for spec in summary.fields:
        python = next(name for name, wire in wire_names.items() if wire == spec.name)
        raw: JsonValue | None = None
        if spec.name in candidates:
            raw = candidates[spec.name]
        elif python in candidates:
            raw = candidates[python]
        if raw is not None or spec.name in candidates or python in candidates:
            outcome: FieldOutcome = _outcome_for(
                entry, spec.name, python, raw, instance_dump, errors
            )
            received: ReceivedValue | None = ReceivedValue(
                type=type(raw).__name__, repr=_short(raw)
            )
        else:
            error = _field_error(errors, spec.name, python)
            if error is not None:
                # Absence itself broke the contract (a required field): the
                # model's own "missing" triple IS the row's outcome.
                outcome = RejectedOutcome(
                    status="rejected",
                    loc=["body", *[str(part) for part in error["loc"]]],
                    msg=error["msg"],
                    type=error["type"],
                )
            else:
                info = entry.model_class.model_fields[python]
                outcome = AbsentOutcome(
                    status="absent",
                    default=None
                    if info.is_required()
                    else _json_safe(info.get_default(call_default_factory=True)),
                )
            received = None
        rows.append(
            ArenaFieldRow(
                field=spec.name,
                rule=spec.rule,
                required=spec.required,
                received=received,
                outcome=outcome,
            )
        )

    triples = _body_triples(errors)
    verdict: Literal["accepted", "rejected"] = "accepted" if instance is not None else "rejected"
    extra_keys = sorted(set(candidates) - known_keys)
    coerced = sum(row.outcome.status == "coerced" for row in rows)
    defaulted = sum(row.outcome.status == "absent" for row in rows)
    if verdict == "accepted":
        reasoning = (
            f"pydantic accepted the candidates for {summary.model}: "
            f"{len(rows)} field(s) judged, {coerced} coerced (original → "
            f"coerced shown per row), {defaulted} absent with the model's "
            "default applied — and the validated dump is the exact instance "
            "the endpoint would hand its handler. The same body against the "
            "notes route would be a 201, not a report."
        )
    else:
        reasoning = (
            f"pydantic refused the candidates for {summary.model}: the "
            f"{len(triples)} error triple(s) are exactly the details array "
            "the 422 validation_failed envelope would carry for this body "
            "— loc prefixed with body, the parameter location FastAPI "
            "reports, {loc, msg, type} normalized by the shared handler. "
            "Fields without their own error passed their own validation; "
            "fix the flagged ones and re-run."
        )
    return ArenaVerdictPayload(
        model=summary,
        roster=list(_ROSTER_SUMMARIES),
        rows=rows,
        verdict=verdict,
        validated=instance_dump,
        errors=triples or None,
        extra_keys_ignored=extra_keys,
        reasoning=reasoning,
    )


def build_arena_roster() -> ArenaRosterPayload:
    """Serve the contenders and their field rules (pure)."""
    return ArenaRosterPayload(
        models=list(_ROSTER_SUMMARIES),
        reasoning=(
            "Three real wire models this server validates elsewhere — pick "
            "one, supply candidate field values, and POST a round: every "
            "outcome comes from the model's own pydantic validation, and "
            "every rejection's {loc, msg, type} triple is exactly what the "
            "422 envelope would report for that body. An unknown model key "
            f"is one of {', '.join(repr(str(key)) for key in get_args(ArenaModelKey))} "
            "away from the edge's own 422."
        ),
    )
