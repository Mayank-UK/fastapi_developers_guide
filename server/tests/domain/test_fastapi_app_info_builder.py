"""Builder unit tests: the app-info payload's pure shaping.

The builder is a pure function over plain data (the router collects the
facts from the live app), so these tests pin exactly: how OpenAPI path
items become route rows (declared methods uppercased and sorted, tags
unioned), that metadata keys and non-string tags never leak into
methods, handler registration ordering, middleware passthrough, and the
stack/docs passthrough — against fixture data shaped like the real
schema, plus one pass over the REAL app's collected facts.
"""

from guide.domain.demos.fastapi_app_info import FastApiAppInfoPayload, build_app_info_payload
from guide.main import create_app

PATHS_FIXTURE: dict[str, dict[str, dict[str, object]]] = {
    "/api/health": {"get": {"tags": ["health"]}},
    "/api/demo/http/headers": {
        "get": {"tags": ["demo:http"]},
        "post": {"tags": ["demo:http"]},
    },
    "/api/content/{topic_id}": {"get": {}},
}


def _payload() -> FastApiAppInfoPayload:
    return build_app_info_payload(
        title="FastAPI Developers Guide",
        version="0.1.0",
        environment="dev",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        stack={"fastapi": "0.143.1", "starlette": "1.8.0", "pydantic": "2.14.1"},
        middleware_names=["RequestIdMiddleware"],
        handler_names={"AppError": "handle_app_error", "Exception": "handle_unexpected_error"},
        paths=PATHS_FIXTURE,
    )


def test_identity_environment_docs_and_stack_pass_through() -> None:
    payload = _payload()
    assert payload.title == "FastAPI Developers Guide"
    assert payload.version == "0.1.0"
    assert payload.environment == "dev"
    assert payload.docs.docs_url == "/docs"
    assert payload.docs.redoc_url == "/redoc"
    assert payload.docs.openapi_url == "/openapi.json"
    assert payload.stack.fastapi == "0.143.1"
    assert payload.stack.starlette == "1.8.0"
    assert payload.stack.pydantic == "2.14.1"


def test_routes_come_sorted_with_uppercased_methods_and_unioned_tags() -> None:
    payload = _payload()
    assert [route.path for route in payload.routes] == [
        "/api/content/{topic_id}",
        "/api/demo/http/headers",
        "/api/health",
    ]
    headers_route = payload.routes[1]
    assert headers_route.methods == ["GET", "POST"]
    assert headers_route.tags == ["demo:http"]
    assert payload.routes[0].tags == []
    assert payload.routes[2].methods == ["GET"]


def test_path_item_metadata_keys_never_become_methods() -> None:
    payload = build_app_info_payload(
        title="t",
        version="v",
        environment="e",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        stack={"fastapi": "f", "starlette": "s", "pydantic": "p"},
        middleware_names=[],
        handler_names={},
        paths={"/x": {"parameters": [], "get": {"tags": ["a", 42, "a"]}}},
    )
    route = payload.routes[0]
    assert route.methods == ["GET"]
    assert route.tags == ["a"]


def test_handler_registrations_are_sorted_by_exception_name() -> None:
    payload = _payload()
    assert [(h.exception, h.handler) for h in payload.exception_handlers] == [
        ("AppError", "handle_app_error"),
        ("Exception", "handle_unexpected_error"),
    ]


def test_real_app_facts_include_health_demo_and_scenario_routes() -> None:
    """The shape the endpoint serves, built from the REAL app's own facts."""
    app = create_app()
    payload = build_app_info_payload(
        title=app.title,
        version=app.version,
        environment="dev",
        docs_url=app.docs_url,
        redoc_url=app.redoc_url,
        openapi_url=app.openapi_url,
        stack={"fastapi": "0.143.1", "starlette": "1.8.0", "pydantic": "2.14.1"},
        middleware_names=[mw.cls.__name__ for mw in app.user_middleware],
        handler_names={
            (key.__name__ if isinstance(key, type) else str(key)): getattr(
                value, "__qualname__", repr(value)
            )
            for key, value in app.exception_handlers.items()
        },
        paths=app.openapi()["paths"],
    )
    routes = {route.path: route for route in payload.routes}
    assert routes["/api/health"].methods == ["GET"]
    assert routes["/api/health"].tags == ["health"]
    assert routes["/api/demo/scenario"].methods == ["GET", "PATCH"]
    assert routes["/api/demo/fastapi/app-info"].methods == ["GET"]
    assert payload.middleware == [
        "CORSMiddleware",
        "SecurityHeadersMiddleware",
        "RequestLogMiddleware",
        "RequestIdMiddleware",
    ]
    handler_names = {h.exception for h in payload.exception_handlers}
    assert {"AppError", "Exception", "HTTPException", "RequestValidationError"} <= handler_names
    # The docs mounts serve the contract but are not part of it.
    assert all(not route.path.startswith("/docs") for route in payload.routes)
    assert all(route.path != "/openapi.json" for route in payload.routes)
