"""The deps-manifest endpoint (topic 31, area ``deps``): the real files, parsed.

Pins the wire contract (GET /api/demo/deps): the panel is parsed AT REQUEST
TIME from the real server/pyproject.toml + server/uv.lock — the groups the
manifest declares, every direct dependency's range beside the lock's exact
pin, the manifest/lock agreement cross-check, the fastapi-rooted direct-vs-
transitive slice, and whole-lock counts. The pure-builder cases feed a tiny
synthetic manifest/lock pair through the SAME public seam to pin the honesty
rules: unjudged operators read not-judged, missing names read '?', drift
reads disagree, and unreadable files degrade instead of failing.
"""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from guide.domain.demos.dep_manifest import build_dep_manifest_payload

PANEL_PATH = "/api/demo/deps"


def row_by_name(body: dict[str, Any], name: str) -> dict[str, Any]:
    """The direct row whose dependency name matches."""
    return next(row for row in body["direct"] if row["name"] == name)


def test_panel_serves_the_real_manifest_and_lock(client: TestClient) -> None:
    response = client.get(PANEL_PATH)
    assert response.status_code == 200
    body = response.json()

    assert body["available"] is True
    assert body["manifestFile"] == "server/pyproject.toml"
    assert body["lockFile"] == "server/uv.lock"
    assert body["requiresPython"] == ">=3.13"
    assert [group["group"] for group in body["groups"]] == ["main", "dev"]
    assert [group["directCount"] for group in body["groups"]] == [20, 7]
    assert body["honestyNote"]

    counts = body["counts"]
    assert counts["direct"] == 27
    assert counts["totalLocked"] == counts["direct"] + counts["transitive"] + 1
    assert counts["totalLocked"] >= 70


def test_direct_rows_carry_constraint_and_locked_pin(client: TestClient) -> None:
    body = client.get(PANEL_PATH).json()

    fastapi_row = row_by_name(body, "fastapi")
    assert fastapi_row["constraint"] == ">=0.115"
    assert fastapi_row["group"] == "main"
    assert fastapi_row["satisfies"] is True
    assert fastapi_row["lockedVersion"] == "0.143.1"

    sqlalchemy_row = row_by_name(body, "sqlalchemy")
    assert sqlalchemy_row["extras"] == "asyncio"
    assert sqlalchemy_row["lockedVersion"] == "2.1.4"

    grpcio_tools = row_by_name(body, "grpcio-tools")
    assert grpcio_tools["group"] == "dev"

    strawberry = row_by_name(body, "strawberry-graphql")
    assert strawberry["extras"] == "fastapi"
    assert strawberry["lockedVersion"] == "0.335.0"


def test_the_manifest_and_lock_agree(client: TestClient) -> None:
    agreement = client.get(PANEL_PATH).json()["agreement"]
    assert agreement["agree"] is True
    assert agreement["manifestNames"] == 20
    assert agreement["lockNames"] == 20
    assert agreement["missingFromLock"] == []
    assert agreement["extraInLock"] == []


def test_the_slice_shows_fastapi_direct_vs_transitive(client: TestClient) -> None:
    tree_slice = client.get(PANEL_PATH).json()["slice"]
    assert tree_slice["root"] == "fastapi"
    assert tree_slice["rootConstraint"] == ">=0.115"
    assert tree_slice["rootLockedVersion"] == "0.143.1"
    children = {child["name"]: child["lockedVersion"] for child in tree_slice["children"]}
    # Nobody wrote these names in the manifest — they arrived as edges.
    assert set(children) == {
        "annotated-doc",
        "opentelemetry-api",
        "pydantic",
        "starlette",
        "typing-extensions",
        "typing-inspection",
    }
    assert children["starlette"] == "1.8.0"
    assert children["pydantic"] == "2.14.1"


def test_the_pure_builder_judges_only_what_it_understands(tmp_path: Path) -> None:
    manifest = tmp_path / "pyproject.toml"
    lock = tmp_path / "uv.lock"
    manifest.write_text(
        "[project]\n"
        'name = "guide"\n'
        "dependencies = [\n"
        '    "ypkg>=2.0",\n'
        '    "eqpkg==1.5.0",\n'
        '    "weirdpkg>=1,<2",\n'
        '    "ghost>=1.0",\n'
        "]\n"
        "[dependency-groups]\n"
        'dev = ["deppkg>=0.1"]\n',
        encoding="utf-8",
    )
    lock.write_text(
        "[[package]]\n"
        'name = "guide"\n'
        'version = "0.1.0"\n'
        'source = { editable = "." }\n'
        "dependencies = [\n"
        '    { name = "eqpkg" },\n'
        '    { name = "weirdpkg" },\n'
        '    { name = "ypkg" },\n'
        "]\n"
        "\n"
        "[package.dev-dependencies]\n"
        'dev = [\n    { name = "deppkg" },\n]\n'
        "\n"
        "[[package]]\n"
        'name = "ypkg"\n'
        'version = "2.4.0"\n'
        "\n"
        "[[package]]\n"
        'name = "eqpkg"\n'
        'version = "1.5.0"\n'
        "\n"
        "[[package]]\n"
        'name = "weirdpkg"\n'
        'version = "1.4.0"\n'
        "\n"
        "[[package]]\n"
        'name = "deppkg"\n'
        'version = "0.3.0"\n',
        encoding="utf-8",
    )

    payload = build_dep_manifest_payload(manifest_path=manifest, lock_path=lock)

    assert payload.available is True
    rows = {row.name: row for row in payload.direct}
    assert rows["ypkg"].satisfies is True  # 2.4.0 >= 2.0
    assert rows["eqpkg"].satisfies is True  # 1.5.0 == 1.5.0
    assert rows["weirdpkg"].satisfies is None  # compound clause: not judged
    assert rows["ghost"].locked_version == "?"  # absent from the lock
    assert rows["ghost"].satisfies is None
    assert rows["deppkg"].group == "dev"

    # The drift the synthetic pair plants is reported, not papered over.
    assert payload.agreement is not None
    assert payload.agreement.agree is False
    assert payload.agreement.missing_from_lock == ["ghost"]

    # The slice root is absent from the synthetic lock: honest empties.
    assert payload.slice is not None
    assert payload.slice.children == []
    assert payload.slice.root_locked_version == "?"


def test_the_pure_builder_degrades_honestly_when_files_are_unreadable(
    tmp_path: Path,
) -> None:
    payload = build_dep_manifest_payload(
        manifest_path=tmp_path / "missing-pyproject.toml",
        lock_path=tmp_path / "missing-uv.lock",
    )
    assert payload.available is False
    assert payload.unavailable_reason is not None
    assert "FileNotFoundError" in payload.unavailable_reason
    assert payload.direct == []
    assert payload.slice is None
    assert payload.counts is None
    assert payload.agreement is None


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][PANEL_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("DepsManifestPanel")
