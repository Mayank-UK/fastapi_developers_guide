"""Routing-explorer demo payload: match a request against the declared table.

``GET /api/demo/routing/explorer?method=…&path=…`` serves this payload. The
demo replays what Starlette's router does for every inbound request — take a
method + path, walk the declared route table, and report the outcome: the
matched template with its extracted path parameters and parsed query
parameters, a 405 with the methods the path DOES declare, a 307
trailing-slash redirect, or a 404 with the nearest declared paths.

The declared table comes from ``app.openapi()["paths"]`` — the same public
choice the app-info demo made, for the same reason: since 0.143 FastAPI's
``include_router`` wraps included routers and the wrapping entries expose no
``.path``, so ``app.routes`` is not a stable surface to read. The matching
itself is an honest simulation of Starlette's semantics for this app: the
default ``str`` converter (``[^/]+``), no implicit HEAD (a HEAD against a
GET-only route is a 405), and ``redirect_slashes`` answered with a 307. One
deliberate simplification: Starlette resolves in REGISTRATION order while
the demo scans templates sorted by path — this app declares no overlapping
templates, so the outcome is identical, and the reasoning says so where it
matters.

The builder is pure: the caller-supplied method/path plus the declared
paths mapping go in, the payload comes out — no I/O, no app access.
"""

import re
from collections.abc import Mapping
from typing import Any, Final, Literal
from urllib.parse import parse_qsl

from guide.core.serialization import CamelModel

_HTTP_METHODS: Final[frozenset[str]] = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)
"""The operation keys an OpenAPI path item can carry; anything else is metadata."""

_PATH_SEGMENT_PARAM: Final[re.Pattern[str]] = re.compile(r"^\{([a-zA-Z_][a-zA-Z0-9_]*)\}$")
"""One template segment like ``{topic_id}`` — Starlette's default str converter."""

_NEAR_MISS_LIMIT: Final[int] = 3
"""How many closest declared paths a 404 reports (the router itself reports none)."""

MatchOutcome = Literal["matched", "redirect", "method_not_allowed", "not_found"]
ParamSource = Literal["path", "query"]


class ExplorerRequest(CamelModel):
    """The simulated request line the caller asked about."""

    method: str
    path: str


class BoundParam(CamelModel):
    """One parameter the router would bind for the handler."""

    name: str
    value: str
    source: ParamSource


class NearMiss(CamelModel):
    """A declared path a 404's caller probably meant (closest by prefix)."""

    path: str
    methods: list[str]


class RoutingExplorerPayload(CamelModel):
    """Wire shape of ``GET /api/demo/routing/explorer`` (absent facts omitted)."""

    request: ExplorerRequest
    route_count: int
    outcome: MatchOutcome
    reasoning: str
    matched_path: str | None = None
    matched_methods: list[str] | None = None
    matched_tags: list[str] | None = None
    path_params: list[BoundParam] = []
    query_params: list[BoundParam] = []
    allowed_methods: list[str] | None = None
    redirect_target: str | None = None
    near_misses: list[NearMiss] | None = None


def _declared_methods(item: Mapping[str, Any]) -> list[str]:
    """The methods one template declares, uppercased and sorted."""
    return sorted(key.upper() for key in item if key in _HTTP_METHODS)


def _declared_tags(item: Mapping[str, Any]) -> list[str]:
    """The tags unioned across one template's operations, sorted."""
    return sorted(
        {
            tag
            for key, operation in item.items()
            if key in _HTTP_METHODS
            for tag in _tag_list(operation)
        }
    )


def _tag_list(operation: Mapping[str, Any]) -> tuple[str, ...]:
    """An operation's tags as a tuple; absent or malformed means none."""
    raw = operation.get("tags")
    if not isinstance(raw, list):
        return ()
    return tuple(tag for tag in raw if isinstance(tag, str))


def _compile_template(template: str) -> re.Pattern[str]:
    """A path template → the regex Starlette's default converter would match.

    ``/api/content/{topic_id}`` becomes ``^/api/content/(?P<topic_id>[^/]+)$``:
    static segments literal, ``{param}`` segments one-or-more non-slash.
    """
    segments = template.strip("/").split("/")
    if segments == [""]:
        return re.compile("^/$")
    parts = [
        f"(?P<{match.group(1)}>[^/]+)"
        if (match := _PATH_SEGMENT_PARAM.match(segment))
        else re.escape(segment)
        for segment in segments
    ]
    return re.compile("^/" + "/".join(parts) + "$")


def _leading_overlap(request_segments: list[str], template: str) -> int:
    """How many leading segments agree (a ``{param}`` segment agrees with any)."""
    score = 0
    for got, want in zip(request_segments, template.strip("/").split("/"), strict=False):
        if _PATH_SEGMENT_PARAM.match(want) or want == got:
            score += 1
        else:
            break
    return score


def _near_misses(
    request_segments: list[str], paths: Mapping[str, Mapping[str, Any]]
) -> list[NearMiss]:
    """The closest declared paths by leading-segment agreement (top 3, score ≥ 1)."""
    scored = sorted(
        ((_leading_overlap(request_segments, template), template) for template in paths),
        key=lambda pair: (-pair[0], pair[1]),
    )
    return [
        NearMiss(path=template, methods=_declared_methods(paths[template]))
        for score, template in scored
        if score >= 1
    ][:_NEAR_MISS_LIMIT]


def _param_list(values: Mapping[str, str], source: ParamSource) -> list[BoundParam]:
    """Wrap extracted values as BoundParams, in declaration/arrival order."""
    return [BoundParam(name=name, value=value, source=source) for name, value in values.items()]


def _quoted(values: list[BoundParam]) -> str:
    """Human rendering of bound parameters for the reasoning sentence."""
    if not values:
        return "none"
    return ", ".join(f"{param.name}='{param.value}'" for param in values)


def build_routing_explorer_payload(
    *,
    method: str,
    path: str,
    paths: Mapping[str, Mapping[str, Any]],
) -> RoutingExplorerPayload:
    """Resolve one simulated request against the declared route table (pure)."""
    raw_path, _, raw_query = path.partition("?")
    query_pairs = parse_qsl(raw_query, keep_blank_values=True)
    query_index: dict[str, str] = {}
    for name, value in query_pairs:
        query_index[name] = value  # last occurrence wins, like a dict-style handler
    request = ExplorerRequest(method=method, path=path)

    for template in sorted(paths):
        match = _compile_template(template).match(raw_path)
        if match is None:
            continue
        methods = _declared_methods(paths[template])
        path_params = _param_list(match.groupdict(), "path")
        query_params = _param_list(query_index, "query")
        if method in methods:
            return RoutingExplorerPayload(
                request=request,
                route_count=len(paths),
                outcome="matched",
                matched_path=template,
                matched_methods=methods,
                matched_tags=_declared_tags(paths[template]),
                path_params=path_params,
                query_params=query_params,
                reasoning=(
                    f"{method} {raw_path} matched the declared template {template}; "
                    f"the router binds path parameter(s) {_quoted(path_params)} and "
                    f"the handler reads query parameter(s) {_quoted(query_params)} "
                    f"before your endpoint function is called."
                ),
            )
        head_note = (
            " There is no implicit HEAD in FastAPI: a GET route does not serve "
            "HEAD requests (topic 03 probed this live) — declare a HEAD route "
            "yourself if you need one."
            if method == "HEAD"
            else ""
        )
        return RoutingExplorerPayload(
            request=request,
            route_count=len(paths),
            outcome="method_not_allowed",
            matched_path=template,
            matched_methods=methods,
            allowed_methods=methods,
            reasoning=(
                f"{method} {raw_path} matched the declared template {template}, but "
                f"that route declares only {', '.join(methods)} — Starlette answers "
                f"405 Method Not Allowed with an allow header naming them, and this "
                f"app's envelope buckets it as not_found (the closest client-error "
                f"kind).{head_note}"
            ),
        )

    toggled = raw_path != "/" and raw_path.endswith("/")
    alternate = raw_path.rstrip("/") if toggled else f"{raw_path}/"
    if alternate != raw_path and any(
        _compile_template(template).match(alternate) is not None for template in paths
    ):
        target = alternate + (f"?{raw_query}" if raw_query else "")
        return RoutingExplorerPayload(
            request=request,
            route_count=len(paths),
            outcome="redirect",
            redirect_target=target,
            reasoning=(
                f"{method} {raw_path} matches no template as written, but the path "
                f"with the trailing slash toggled ({alternate}) does — Starlette's "
                f"redirect_slashes answers 307 Temporary Redirect to {target}, "
                f"preserving method and query, and the browser re-issues the request "
                f"there (topic 04's curl tour watched /docs/ do this)."
            ),
        )

    misses = _near_misses(raw_path.strip("/").split("/"), paths)
    near_sentence = (
        f" Closest declared paths: {', '.join(miss.path for miss in misses)}." if misses else ""
    )
    return RoutingExplorerPayload(
        request=request,
        route_count=len(paths),
        outcome="not_found",
        near_misses=misses,
        reasoning=(
            f"{method} {raw_path} matched none of the {len(paths)} declared route "
            f"templates — the router hands back a 404, which this app renders as "
            f"the shared not_found envelope (a real curl tour produces one at the "
            f"bottom of this topic).{near_sentence}"
        ),
    )
