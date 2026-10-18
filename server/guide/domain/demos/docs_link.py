"""Docs-link demo payload: the running app's generated documentation, linked.

``GET /api/demo/api/docs-link`` serves this payload — topic 12's demo. The
endpoint introspects the SAME schema ``/openapi.json`` serves (via
``app.openapi()``, cached after the first call — the stable public view of
the declared API, per the 0.143 ``app.routes`` gotcha topic 04 recorded)
and shapes a documentation hub from it: where the rendered docs live
(Swagger UI at ``/docs``, ReDoc at ``/redoc``, the contract itself at
``/openapi.json``), the schema's ``info`` identity, the path/operation/
area counts, the component schema names, the posts resource's generated
operations, and one SHOWCASE slice — the ``POST /api/posts`` operation
exactly as generated, so the reader watches a declaration they wrote in
topic 11 become a documented operation with zero schema authored by hand.

The builder is pure: the app's collected facts + the schema mapping go
in, the payload comes out — no I/O, no app access. Every count and name
in the payload comes from the live schema, and absent facts (a disabled
docs mount, an operation without a ``$ref``) stay honestly absent rather
than being invented.
"""

from collections.abc import Mapping
from typing import Any, Final

from guide.core.serialization import CamelModel

_HTTP_METHODS: Final[frozenset[str]] = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)
"""The operation keys an OpenAPI path item can carry; anything else is metadata."""

_UNTAGGED: Final[str] = "untagged"
"""The area name for operations no router tagged (none in this app today)."""

POSTS_TAG: Final[str] = "posts"
"""The area this demo spotlights: topic 11's real resource."""

SHOWCASE_METHOD: Final[str] = "post"
SHOWCASE_PATH: Final[str] = "/api/posts"
"""The one operation the payload slices in full: the posts create."""


class DocsLocations(CamelModel):
    """Where the framework's rendered documentation surfaces live."""

    swagger_ui: str | None
    redoc: str | None
    openapi_json: str | None


class AreaFact(CamelModel):
    """One documentation area (an OpenAPI tag) with its live shape."""

    tag: str
    paths: int
    operations: int
    methods: list[str]


class PostsOperationFact(CamelModel):
    """One generated operation of the posts resource, as /openapi.json has it."""

    method: str
    path: str
    operation_id: str
    summary: str
    description: str
    responses: list[str]


class ShowcaseFact(CamelModel):
    """The POST /api/posts operation, sliced straight from the schema."""

    method: str
    path: str
    summary: str
    description: str
    operation_id: str
    tags: list[str]
    request_schema: str | None = None
    success_status: str | None = None
    success_schema: str | None = None
    validation_schema: str | None = None


class DocsLinkPayload(CamelModel):
    """Wire shape of ``GET /api/demo/api/docs-link`` (absent facts omitted)."""

    info_title: str
    info_version: str
    openapi_version: str
    docs: DocsLocations
    path_count: int
    operation_count: int
    area_count: int
    areas: list[AreaFact]
    schema_count: int
    schema_names: list[str]
    posts_operations: list[PostsOperationFact]
    showcase: ShowcaseFact | None = None
    reasoning: str


def _tag_list(operation: Mapping[str, Any]) -> tuple[str, ...]:
    """An operation's tags as a tuple; absent or malformed means none."""
    raw = operation.get("tags")
    if not isinstance(raw, list):
        return ()
    return tuple(tag for tag in raw if isinstance(tag, str))


def _string_fact(operation: Mapping[str, Any], key: str) -> str:
    """A text fact (summary/description/operationId); absent means empty."""
    raw = operation.get(key)
    return raw if isinstance(raw, str) else ""


def _ref_name(value: Any) -> str | None:
    """The component name a ``$ref`` points at (``#/components/schemas/X`` → X)."""
    if not isinstance(value, Mapping):
        return None
    ref = value.get("$ref")
    if not isinstance(ref, str) or not ref:
        return None
    return ref.rsplit("/", 1)[-1]


def _json_schema(operation: Mapping[str, Any], response_status: str) -> Any:
    """The JSON schema a response status carries; None when it has none."""
    responses = operation.get("responses")
    if not isinstance(responses, Mapping):
        return None
    status = responses.get(response_status)
    if not isinstance(status, Mapping):
        return None
    content = status.get("content")
    if not isinstance(content, Mapping):
        return None
    json_body = content.get("application/json")
    if not isinstance(json_body, Mapping):
        return None
    return json_body.get("schema")


def _request_schema(operation: Mapping[str, Any]) -> str | None:
    """The request body's component name, if the operation declares one."""
    request_body = operation.get("requestBody")
    if not isinstance(request_body, Mapping):
        return None
    content = request_body.get("content")
    if not isinstance(content, Mapping):
        return None
    json_body = content.get("application/json")
    if not isinstance(json_body, Mapping):
        return None
    return _ref_name(json_body.get("schema"))


def _iter_operations(
    paths: Mapping[str, Mapping[str, Any]],
) -> list[tuple[str, str, Mapping[str, Any]]]:
    """Every (method, path, operation) in the schema, in stable sorted order."""
    operations: list[tuple[str, str, Mapping[str, Any]]] = []
    for path, item in sorted(paths.items()):
        if not isinstance(item, Mapping):
            continue
        for method, operation in item.items():
            if method in _HTTP_METHODS and isinstance(operation, Mapping):
                operations.append((method, path, operation))
    return operations


def _areas(operations: list[tuple[str, str, Mapping[str, Any]]]) -> list[AreaFact]:
    """Group every operation under its tags: one AreaFact per tag, sorted."""
    by_tag: dict[str, dict[str, Any]] = {}
    for method, path, operation in operations:
        tags = _tag_list(operation) or (_UNTAGGED,)
        for tag in tags:
            area = by_tag.setdefault(tag, {"paths": set(), "operations": 0, "methods": set()})
            area["paths"].add(path)
            area["operations"] += 1
            area["methods"].add(method.upper())
    return [
        AreaFact(
            tag=tag,
            paths=len(by_tag[tag]["paths"]),
            operations=by_tag[tag]["operations"],
            methods=sorted(by_tag[tag]["methods"]),
        )
        for tag in sorted(by_tag)
    ]


def _posts_operations(
    operations: list[tuple[str, str, Mapping[str, Any]]],
) -> list[PostsOperationFact]:
    """The posts resource's generated operations, method-sorted within a path."""
    facts = [
        PostsOperationFact(
            method=method.upper(),
            path=path,
            operation_id=_string_fact(operation, "operationId"),
            summary=_string_fact(operation, "summary"),
            description=_string_fact(operation, "description"),
            responses=sorted(str(status) for status in _response_statuses(operation)),
        )
        for method, path, operation in operations
        if POSTS_TAG in _tag_list(operation)
    ]
    return sorted(facts, key=lambda fact: (fact.path, fact.method))


def _response_statuses(operation: Mapping[str, Any]) -> list[str]:
    """The response status keys an operation documents."""
    responses = operation.get("responses")
    if not isinstance(responses, Mapping):
        return []
    return [status for status in responses if isinstance(status, str)]


def _showcase(paths: Mapping[str, Mapping[str, Any]]) -> ShowcaseFact | None:
    """Slice the POST /api/posts operation exactly as generated, or None."""
    item = paths.get(SHOWCASE_PATH)
    if not isinstance(item, Mapping):
        return None
    operation = item.get(SHOWCASE_METHOD)
    if not isinstance(operation, Mapping):
        return None
    success_status = next(
        (status for status in _response_statuses(operation) if status.startswith("2")),
        None,
    )
    return ShowcaseFact(
        method=SHOWCASE_METHOD.upper(),
        path=SHOWCASE_PATH,
        summary=_string_fact(operation, "summary"),
        description=_string_fact(operation, "description"),
        operation_id=_string_fact(operation, "operationId"),
        tags=list(_tag_list(operation)),
        request_schema=_request_schema(operation),
        success_status=success_status,
        success_schema=(
            _ref_name(_json_schema(operation, success_status))
            if success_status is not None
            else None
        ),
        validation_schema=_ref_name(_json_schema(operation, "422")),
    )


def build_docs_link_payload(
    *,
    title: str,
    version: str,
    docs_url: str | None,
    redoc_url: str | None,
    openapi_url: str | None,
    schema: Mapping[str, Any],
) -> DocsLinkPayload:
    """Shape the running app's documentation facts into the payload (pure)."""
    raw_paths = schema.get("paths")
    paths: Mapping[str, Mapping[str, Any]] = raw_paths if isinstance(raw_paths, Mapping) else {}
    operations = _iter_operations(paths)
    areas = _areas(operations)
    raw_components = schema.get("components")
    raw_schemas = raw_components.get("schemas") if isinstance(raw_components, Mapping) else None
    schema_names = (
        sorted(name for name in raw_schemas if isinstance(name, str))
        if isinstance(raw_schemas, Mapping)
        else []
    )
    raw_openapi_version = schema.get("openapi")
    openapi_version = raw_openapi_version if isinstance(raw_openapi_version, str) else "unknown"
    posts_operations = _posts_operations(operations)
    showcase = _showcase(paths)

    swagger_note = docs_url if docs_url is not None else "(disabled)"
    redoc_note = redoc_url if redoc_url is not None else "(disabled)"
    contract_note = openapi_url if openapi_url is not None else "(disabled)"
    showcase_sentence = (
        (
            f"The showcase slice is the {showcase.method} {showcase.path} operation "
            f"exactly as generated — its summary, description, operationId, and "
            f"$ref names were read from the schema, not restated by hand."
        )
        if showcase is not None
        else "The posts create operation is not in this schema, so no slice is shown."
    )
    return DocsLinkPayload(
        info_title=title,
        info_version=version,
        openapi_version=openapi_version,
        docs=DocsLocations(swagger_ui=docs_url, redoc=redoc_url, openapi_json=openapi_url),
        path_count=len(paths),
        operation_count=len(operations),
        area_count=len(areas),
        areas=areas,
        schema_count=len(schema_names),
        schema_names=schema_names,
        posts_operations=posts_operations,
        showcase=showcase,
        reasoning=(
            f"Every fact here was read from the same OpenAPI document the running "
            f"app serves at {contract_note} — {len(paths)} paths holding "
            f"{len(operations)} operations across {len(areas)} tag areas, with "
            f"{len(schema_names)} component schemas under components/schemas. "
            f"No line of that schema was written by hand: the routes' decorators, "
            f"docstrings, response_model declarations, and tags ARE the authoring. "
            f"Open {swagger_note} (Swagger UI) or {redoc_note} (ReDoc) in a browser "
            f"to read the same contract rendered. {showcase_sentence}"
        ),
    )
