"""Runtime-types demo payload: types AT RUNTIME, on real guide objects.

``GET /api/demo/py/runtime-types`` serves this payload. The module is
deliberately written under ``from __future__ import annotations`` (PEP 563):
every annotation below is stored as a *string* until something resolves it —
which is exactly the contrast the demo proves. Raw ``__annotations__`` on
``repeat`` show strings; ``typing.get_type_hints`` shows resolved objects;
on the eagerly-annotated registry method both agree. Nothing here is I/O or
state: the builder is a pure function the thin router calls.
"""

from __future__ import annotations

import types
from dataclasses import MISSING, fields
from typing import Any, Final, Literal, get_args, get_origin, get_type_hints

from pydantic import ValidationError

from guide.content.models import Section, Topic
from guide.content.registry import ContentRegistry
from guide.content.snippet_matcher import SnippetMatch
from guide.core.errors import ErrorBody
from guide.core.serialization import CamelModel


def repeat(text: str, times: int) -> str:
    """The enforcement proof: annotated, but never checked at runtime.

    Called as ``repeat(3.0, 2)`` this runs happily and returns ``6.0`` — a
    ``float`` where ``-> str`` was declared. CPython does not look at the
    annotations; mypy does, and rejects the call.
    """
    return text * times


_NONE_TYPE: Final = type(None)
"""``None`` as a type object — what ``X | None`` actually stores on the right."""


def _display(annotation: object) -> str:
    """A stable, readable name for one type object (the demo's label maker).

    Recurses into generic aliases and unions, and strips ``Annotated``
    metadata — the same walk ``get_origin``/``get_args`` make possible.
    """
    if annotation is _NONE_TYPE:
        return "None"
    if annotation is Any:
        return "Any"
    if annotation is Ellipsis:
        return "..."
    if hasattr(annotation, "__metadata__"):  # typing.Annotated — drop the metadata
        return _display(get_args(annotation)[0])
    if isinstance(annotation, types.UnionType):  # the PEP 604 ``X | Y`` object
        return " | ".join(_display(arg) for arg in get_args(annotation))
    origin = get_origin(annotation)
    if origin is not None:  # a subscribed alias: list[int], dict[str, Topic], …
        inner = ", ".join(_display(arg) for arg in get_args(annotation))
        return f"{_origin_name(origin)}[{inner}]"
    if isinstance(annotation, type):
        return annotation.__qualname__
    return str(annotation)


def _origin_name(origin: object) -> str:
    """``list`` for ``list[int]``, ``UnionType`` for ``X | Y``, and so on."""
    return getattr(origin, "__name__", str(origin))


class AnnotationRow(CamelModel):
    """One name annotated by a symbol: the raw entry vs the resolved hint."""

    name: str
    raw: str
    resolved: str


class SymbolHints(CamelModel):
    """Raw ``__annotations__`` vs ``get_type_hints`` for one real symbol."""

    symbol: str
    mode: Literal["deferred", "eager"]
    rows: list[AnnotationRow]


class OriginArgsRow(CamelModel):
    """How ``get_origin``/``get_args`` split one real generic annotation."""

    symbol: str
    alias: str
    origin: str
    args: list[str]


class FieldRow(CamelModel):
    """One field an introspection API reports, with its requiredness."""

    name: str
    annotation: str
    required: bool


class FieldFaceOff(CamelModel):
    """``dataclasses.fields`` vs ``pydantic.model_fields``, same walk."""

    dataclass_symbol: str
    dataclass_fields: list[FieldRow]
    pydantic_symbol: str
    pydantic_fields: list[FieldRow]


class EnforcementRun(CamelModel):
    """The proof that a wrong-typed call runs — and returns — anyway."""

    function: str
    signature: str
    call: str
    declared_return: str
    actual_return: str
    returned_value: str
    mypy_verdict: str


class BoundaryCheck(CamelModel):
    """The counterpoint: pydantic DOES enforce — when you ask it to."""

    model: str
    bad_input: str
    outcome: str
    error_type: str
    message: str


class RuntimeTypesPayload(CamelModel):
    """Wire shape of ``GET /api/demo/py/runtime-types`` (camelCase)."""

    hints_vs_raw: list[SymbolHints]
    origin_args: list[OriginArgsRow]
    face_off: FieldFaceOff
    enforcement: EnforcementRun
    boundary: BoundaryCheck


def _annotation_rows(annotations: dict[str, Any], resolved: dict[str, Any]) -> list[AnnotationRow]:
    """Pair each raw annotation with its resolved hint, in declaration order."""
    return [
        AnnotationRow(
            name=name,
            raw=repr(value) if isinstance(value, str) else _display(value),
            resolved=_display(resolved[name]),
        )
        for name, value in annotations.items()
    ]


def _symbol_hints() -> list[SymbolHints]:
    """Two real symbols: one deferred (this module), one eager (the registry)."""
    deferred = repeat
    eager = ContentRegistry.topic_by_id
    return [
        SymbolHints(
            symbol=f"{deferred.__module__}.{deferred.__qualname__}",
            mode="deferred",
            rows=_annotation_rows(deferred.__annotations__, get_type_hints(deferred)),
        ),
        SymbolHints(
            symbol=f"{eager.__module__}.{eager.__qualname__}",
            mode="eager",
            rows=_annotation_rows(eager.__annotations__, get_type_hints(eager)),
        ),
    ]


def _origin_row(symbol: str, annotation: object) -> OriginArgsRow:
    """Split one annotation into its origin (the constructor) and args."""
    origin = get_origin(annotation)
    return OriginArgsRow(
        symbol=symbol,
        alias=_display(annotation),
        origin=_origin_name(origin) if origin is not None else _display(annotation),
        args=[_display(arg) for arg in get_args(annotation)],
    )


def _origin_args_rows() -> list[OriginArgsRow]:
    """``get_origin``/``get_args`` on real guide annotations + a control alias."""
    return [
        _origin_row("list[int]", list[int]),
        _origin_row("Section.blocks", get_type_hints(Section)["blocks"]),
        _origin_row("ErrorBody.details", get_type_hints(ErrorBody)["details"]),
        _origin_row(
            "ContentRegistry.topic_by_id (return)",
            get_type_hints(ContentRegistry.topic_by_id)["return"],
        ),
    ]


def _face_off() -> FieldFaceOff:
    """The introspection face-off: dataclass fields vs pydantic model fields."""
    return FieldFaceOff(
        dataclass_symbol="guide.content.snippet_matcher.SnippetMatch",
        dataclass_fields=[
            FieldRow(
                name=field.name,
                annotation=_display(field.type),
                required=field.default is MISSING,
            )
            for field in fields(SnippetMatch)
        ],
        pydantic_symbol="guide.content.models.Topic",
        pydantic_fields=[
            FieldRow(
                name=name,
                annotation=_display(field_info.annotation),
                required=field_info.is_required(),
            )
            for name, field_info in Topic.model_fields.items()
        ],
    )


def _enforcement() -> EnforcementRun:
    """Call ``repeat`` with a wrong type; report that it ran anyway."""
    # Silencing mypy IS the demo: a float where str is declared.
    value = repeat(3.0, 2)  # type: ignore[arg-type]
    return EnforcementRun(
        function="repeat",
        signature="def repeat(text: str, times: int) -> str",
        call="repeat(3.0, 2)",
        declared_return="str",
        actual_return=type(value).__name__,
        returned_value=repr(value),
        mypy_verdict=(
            'mypy (strict) rejects the call before it ever runs: '
            'Argument 1 to "repeat" has incompatible type "float"; expected "str"'
        ),
    )


def _boundary() -> BoundaryCheck:
    """Hand a str-declared field an int; pydantic v2 refuses to coerce it."""
    try:
        Topic.model_validate(
            {
                "id": 123,
                "title": "Contraband",
                "group": "foundations",
                "order": 1,
                "sections": [],
            }
        )
    except ValidationError as exc:
        error = exc.errors()[0]
        return BoundaryCheck(
            model="Topic",
            bad_input='{"id": 123, "title": "Contraband", …}',
            outcome="rejected",
            error_type=error["type"],
            message=error["msg"],
        )
    raise AssertionError("pydantic must reject an int where Topic declares str")


def build_runtime_types_payload() -> RuntimeTypesPayload:
    """Assemble the whole demo payload from real guide objects (pure, no I/O)."""
    return RuntimeTypesPayload(
        hints_vs_raw=_symbol_hints(),
        origin_args=_origin_args_rows(),
        face_off=_face_off(),
        enforcement=_enforcement(),
        boundary=_boundary(),
    )
