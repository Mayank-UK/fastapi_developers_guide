"""Docs-link builder: the pure hub against fixture OpenAPI schemas.

The builder is the demo's engine — counting paths/operations/areas,
naming component schemas, slicing the posts POST operation with its
``$ref`` names — so these tests pin each fact against small hand-authored
schemas, independent of the live app, including the honest-absent paths
(empty schema, disabled docs mounts, operations without refs).
"""

from guide.domain.demos.docs_link import build_docs_link_payload

SCHEMA = {
    "openapi": "3.1.0",
    "paths": {
        "/api/health": {"get": {"tags": ["health"], "operationId": "read_health"}},
        "/api/posts": {
            "get": {"tags": ["posts"], "summary": "List Posts"},
            "post": {
                "tags": ["posts"],
                "summary": "Create Post",
                "description": "Create from the validated body.",
                "operationId": "create_post_api_posts_post",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/PostCreate"}}
                    },
                },
                "responses": {
                    "201": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Post"}}
                        }
                    },
                    "422": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                            }
                        }
                    },
                },
            },
        },
        "/api/posts/{post_id}": {
            "put": {"tags": ["posts"], "operationId": "replace_post"}
        },
    },
    "components": {"schemas": {"Post": {}, "PostCreate": {}, "HTTPValidationError": {}}},
}


def build(schema: object = SCHEMA) -> object:
    return build_docs_link_payload(
        title="Fixture API",
        version="1.2.3",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        schema=schema,  # type: ignore[arg-type]
    )


def test_counts_paths_operations_areas_and_schemas() -> None:
    payload = build()
    assert payload.path_count == 3
    assert payload.operation_count == 4
    assert payload.area_count == 2
    assert payload.schema_count == 3
    assert payload.schema_names == ["HTTPValidationError", "Post", "PostCreate"]


def test_areas_carry_methods_and_operation_counts() -> None:
    payload = build()
    by_tag = {area.tag: area for area in payload.areas}
    assert by_tag["posts"].methods == ["GET", "POST", "PUT"]
    assert by_tag["posts"].operations == 3
    assert by_tag["posts"].paths == 2
    assert by_tag["health"].methods == ["GET"]


def test_posts_operations_are_sorted_with_generated_ids() -> None:
    payload = build()
    assert [(op.method, op.path) for op in payload.posts_operations] == [
        ("GET", "/api/posts"),
        ("POST", "/api/posts"),
        ("PUT", "/api/posts/{post_id}"),
    ]
    create = payload.posts_operations[1]
    assert create.operation_id == "create_post_api_posts_post"
    assert create.summary == "Create Post"
    assert create.description == "Create from the validated body."
    assert create.responses == ["201", "422"]


def test_showcase_slices_the_create_operation_with_its_refs() -> None:
    payload = build()
    assert payload.showcase is not None
    showcase = payload.showcase
    assert showcase.summary == "Create Post"
    assert showcase.request_schema == "PostCreate"
    assert showcase.success_status == "201"
    assert showcase.success_schema == "Post"
    assert showcase.validation_schema == "HTTPValidationError"
    assert "read from the schema" in payload.reasoning


def test_untagged_operations_group_under_an_honest_area() -> None:
    payload = build(
        {
            "openapi": "3.1.0",
            "paths": {"/lonely": {"get": {"operationId": "no_tags"}}},
        }
    )
    assert [(area.tag, area.methods) for area in payload.areas] == [("untagged", ["GET"])]


def test_empty_schema_stays_honest_zero_counts_no_showcase() -> None:
    payload = build({"openapi": "3.1.0", "paths": {}})
    assert payload.path_count == 0
    assert payload.operation_count == 0
    assert payload.areas == []
    assert payload.posts_operations == []
    assert payload.showcase is None
    assert "not in this schema" in payload.reasoning


def test_malformed_schema_degrades_to_empty_facts() -> None:
    payload = build({"openapi": 3, "paths": None, "components": "nope"})
    assert payload.openapi_version == "unknown"
    assert payload.path_count == 0
    assert payload.schema_names == []
    assert payload.showcase is None


def test_disabled_docs_mounts_stay_absent_not_invented() -> None:
    payload = build_docs_link_payload(
        title="T",
        version="0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        schema=SCHEMA,
    )
    assert payload.docs.swagger_ui is None
    assert payload.docs.redoc is None
    assert payload.docs.openapi_json is None
    assert "(disabled)" in payload.reasoning


def test_operation_without_refs_leaves_showcase_refs_absent() -> None:
    payload = build(
        {
            "openapi": "3.1.0",
            "paths": {
                "/api/posts": {
                    "post": {
                        "tags": ["posts"],
                        "responses": {"204": {"description": "No Content"}},
                    }
                }
            },
        }
    )
    assert payload.showcase is not None
    assert payload.showcase.request_schema is None
    assert payload.showcase.success_status == "204"
    assert payload.showcase.success_schema is None
    assert payload.showcase.validation_schema is None


def test_error_responses_only_means_no_success_status() -> None:
    payload = build(
        {
            "openapi": "3.1.0",
            "paths": {
                "/api/posts": {
                    "post": {"tags": ["posts"], "responses": {"422": {}, "500": {}}}
                }
            },
        }
    )
    assert payload.showcase is not None
    assert payload.showcase.success_status is None
    assert payload.showcase.success_schema is None
