"""Pydantic validation lab: the pydantic topic's demo payload builders.

``GET /api/demo/pyd/lab/schema`` and ``POST /api/demo/pyd/lab/validate``
serve these payloads. The lab makes pydantic's validation pipeline VISIBLE:
the request model deliberately declares permissive unions so each scalar
keeps exactly what JSON carried (a smart union prefers the exact type —
``"42"`` stays ``str``), and the builder then re-runs every field through
its strict target type via ``TypeAdapter`` in pydantic's default (lax)
mode, reporting raw-vs-coerced per field — including the constraint error
types (``greater_than_equal`` …) and the ``@field_validator`` /
``@model_validator`` behavior defined on ``LabSpecimen``.

When a body cannot even parse into ``LabRequest`` (a non-list ``tags``, a
non-string ``handle``, a missing field), FastAPI answers with its own 422
envelope before this module runs — that path is part of the lesson, and
the client demo renders it through the family error panel.

The builders are pure: plain data in, payload out — no I/O, no state.
"""

from typing import Annotated, Any, Final, Literal

from pydantic import (
    AfterValidator,
    Field,
    JsonValue,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from guide.core.serialization import CamelModel

CountValue = int | float | str
"""Number-or-numeric-string: JSON scalars a raw ``count`` may arrive as."""

FlagValue = bool | int | str
"""Boolean spellings: ``true``, ``1``, ``"true"``, ``"on"`` … kept as sent."""

ScoreValue = int | float | str
"""Score raw spellings; the specimen's bounds judge the coerced integer."""


def canonical_handle(value: str) -> str:
    """Canonical demo handle: lowercase, whitespace collapsed to hyphens."""
    return "-".join(value.lower().split())


class LabRequest(CamelModel):
    """Permissive POST body: each scalar keeps EXACTLY what JSON carried.

    The unions are the point — pydantic's smart union matching prefers the
    exact runtime type, so ``"42"`` arrives here still a ``str`` and ``4.0``
    still a ``float``. ``tags`` and the required-ness of every field stay
    strict: shapes the lab cannot honestly echo are refused by FastAPI's
    own 422 before the report is built.
    """

    count: CountValue
    flag: FlagValue
    tags: list[str]
    score: ScoreValue
    handle: str


ScoreField = Annotated[int, Field(ge=1, le=100)]
"""The constrained target: coercion first, then the 1..100 bounds."""

HandleField = Annotated[str, AfterValidator(canonical_handle)]
"""The validator-as-type target: any string, then canonicalized."""


class LabSpecimen(CamelModel):
    """The strict model a fully-validated submission becomes.

    Every field declares its target type; ``score`` carries ``Field``
    bounds; ``handle`` is normalized by a real ``@field_validator``; and a
    ``@model_validator`` cross-field rule no single field could express.
    ``GET /api/demo/pyd/lab/schema`` serves this model's generated JSON
    Schema, so the schema and the enforcement cannot drift apart.
    """

    count: int
    flag: bool
    tags: list[str]
    score: ScoreField
    handle: str

    @field_validator("handle")
    @classmethod
    def canonicalize_handle(cls, value: str) -> str:
        """Delegate to ``canonical_handle`` — one rule, reused by the report."""
        return canonical_handle(value)

    @model_validator(mode="after")
    def flag_needs_tags(self) -> "LabSpecimen":
        """Cross-field rule: an enabled experiment carries at least one tag."""
        if self.flag and not self.tags:
            raise ValueError("flag requires at least one tag")
        return self


class ReceivedValue(CamelModel):
    """What one field actually carried on the wire: type name + repr."""

    type: str
    repr: str


class CleanOutcome(CamelModel):
    """The raw value already was the target type and value."""

    status: Literal["clean"]
    value: JsonValue
    value_type: str


class CoercedOutcome(CamelModel):
    """Lax coercion changed the value (or its type) to satisfy the target."""

    status: Literal["coerced"]
    value: JsonValue
    value_type: str
    from_type: str


class RejectedOutcome(CamelModel):
    """The target refused the raw value — pydantic's own error type + msg."""

    status: Literal["rejected"]
    error_type: str
    message: str


FieldOutcome = Annotated[
    CleanOutcome | CoercedOutcome | RejectedOutcome, Field(discriminator="status")
]
"""Discriminated on ``status`` — same pattern as the content model's blocks."""


class FieldReport(CamelModel):
    """One lab field: the rule applied, the raw input, the outcome."""

    field: str
    rule: str
    received: ReceivedValue
    outcome: FieldOutcome


class SpecimenError(CamelModel):
    """One ``LabSpecimen`` rejection, normalized like the 422 details."""

    loc: list[str]
    msg: str
    type: str


class PydLabReportPayload(CamelModel):
    """Wire shape of ``POST /api/demo/pyd/lab/validate`` (camelCase)."""

    rows: list[FieldReport]
    specimen_valid: bool
    specimen: dict[str, JsonValue] | None = None
    specimen_errors: list[SpecimenError] | None = None


class PydLabSchemaPayload(CamelModel):
    """Wire shape of ``GET /api/demo/pyd/lab/schema`` (camelCase)."""

    model: str
    json_schema: dict[str, JsonValue]


_MAX_REPR: Final = 80
"""Received reprs are capped so a hostile mega-payload cannot bloat the wire."""


def _short(value: object) -> str:
    """Cap a repr at ``_MAX_REPR`` characters, ellipsis-marked when longer."""
    text = repr(value)
    return text if len(text) <= _MAX_REPR else text[:_MAX_REPR] + "…"


def _received(value: object) -> ReceivedValue:
    """Describe the raw value exactly as the request model retained it."""
    return ReceivedValue(type=type(value).__name__, repr=_short(value))


_TARGETS: Final[dict[str, tuple[str, TypeAdapter[Any]]]] = {
    "count": ("int — numeric strings and whole floats coerce, lax mode", TypeAdapter(int)),
    "flag": ('bool — "true"/"on"/1/0 coerce; arbitrary strings do not', TypeAdapter(bool)),
    "tags": ("list[str] — any sequence coerces, items must be strings", TypeAdapter(list[str])),
    "score": ("int, Field(ge=1, le=100) — coerce first, then the bounds", TypeAdapter(ScoreField)),
    "handle": ("str + @field_validator — canonical_handle normalizes", TypeAdapter(HandleField)),
}
"""Field name → (the rule shown in the report, its strict target adapter)."""

_FIELDS: Final[tuple[str, ...]] = ("count", "flag", "tags", "score", "handle")
"""Report order: the declaration order of LabRequest's fields."""


def _field_report(name: str, raw: object) -> FieldReport:
    """Run one raw field through its strict target; report the outcome."""
    rule, adapter = _TARGETS[name]
    try:
        coerced = adapter.validate_python(raw)
    except ValidationError as exc:
        error = exc.errors()[0]
        return FieldReport(
            field=name,
            rule=rule,
            received=_received(raw),
            outcome=RejectedOutcome(
                status="rejected", error_type=error["type"], message=error["msg"]
            ),
        )
    outcome: CleanOutcome | CoercedOutcome
    if type(coerced) is type(raw) and coerced == raw:
        outcome = CleanOutcome(status="clean", value=coerced, value_type=type(coerced).__name__)
    else:
        outcome = CoercedOutcome(
            status="coerced",
            value=coerced,
            value_type=type(coerced).__name__,
            from_type=type(raw).__name__,
        )
    return FieldReport(field=name, rule=rule, received=_received(raw), outcome=outcome)


def build_validation_report(request: LabRequest) -> PydLabReportPayload:
    """Per-field coercion report + the whole-specimen verdict (pure)."""
    rows = [_field_report(name, getattr(request, name)) for name in _FIELDS]
    try:
        specimen = LabSpecimen.model_validate(request.model_dump())
    except ValidationError as exc:
        return PydLabReportPayload(
            rows=rows,
            specimen_valid=False,
            specimen_errors=[
                SpecimenError(
                    loc=[str(part) for part in error["loc"]],
                    msg=error["msg"],
                    type=error["type"],
                )
                for error in exc.errors()
            ],
        )
    return PydLabReportPayload(
        rows=rows,
        specimen_valid=True,
        specimen=specimen.model_dump(mode="json"),
    )


def build_schema_payload() -> PydLabSchemaPayload:
    """The specimen's generated JSON Schema — introspection, not hand-writing."""
    return PydLabSchemaPayload(
        model=LabSpecimen.__name__,
        json_schema=LabSpecimen.model_json_schema(),
    )
