"""The deploy-stack endpoint (topic 37, area ``deploy``).

Pins the wire contract (GET /api/demo/deploy/stack): the runtime block
of live process facts (interpreter, pid, command line, a REAL internal
GET /api/health through the serving app), the eight deploy-surface areas
with verdicts that are only ever pass/fail/manual, the repo-root
visibility gate behaving honestly in BOTH directions (real file checks
when the repo is mounted — the dev container and the host — honest
manual rows when it is not — the live server container's server/-only
bind mount), the AppConfig row verifying everywhere because it reads the
server tree, and the pure builder judging a broken tree as fail rather
than crashing.
"""

import os
import platform
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guide.core.config import get_config
from guide.domain.demos.deploy_stack import build_deploy_stack_payload, default_roots

STACK_PATH = "/api/demo/deploy/stack"

EXPECTED_AREA_IDS = [
    "platform",
    "app-stack",
    "edge",
    "images",
    "pipeline",
    "release",
    "parity",
    "kubernetes",
]

RUNTIME_ROW_IDS = [
    "env",
    "python",
    "pid",
    "command",
    "graceful-shutdown",
    "workers",
    "reload",
    "health",
]

REPO_ROOT_ROW_IDS = [
    "platform-services",
    "image-pins",
    "image-rail",
    "env-rails",
    "nginx-app-server",
    "multi-stage-uv",
    "ci-contract",
    "blue-green-boot",
    "template-boots",
]


def rows_by_area(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every stack row flat-mapped by id (ids are unique per panel)."""
    return {row["id"]: row for area in body["areas"] for row in area["items"]}


def test_runtime_rows_are_live_process_facts(client: TestClient) -> None:
    body = client.get(STACK_PATH).json()
    assert [row["id"] for row in body["runtime"]] == RUNTIME_ROW_IDS
    by_id = {row["id"]: row for row in body["runtime"]}
    assert by_id["env"]["value"] == get_config().env, "the env the app booted in"
    assert by_id["python"]["value"] == platform.python_version()
    assert by_id["pid"]["value"] == str(os.getpid())
    # The health fact is a REAL round through the serving app.
    assert by_id["health"]["value"].startswith("200 {"), "the probe hit the real route"
    assert '"status":"ok"' in by_id["health"]["value"]


def test_panel_serves_the_eight_areas_with_consistent_verdicts(client: TestClient) -> None:
    response = client.get(STACK_PATH)
    assert response.status_code == 200
    body = response.json()
    assert [area["id"] for area in body["areas"]] == EXPECTED_AREA_IDS
    assert all(area["note"] for area in body["areas"])
    every = [row for area in body["areas"] for row in area["items"]]
    assert len(every) >= 20, "the deploy surface earns its keep in rows"
    for row in every:
        assert row["verdict"] in ("pass", "fail", "manual")
        assert row["checkKind"] in ("live", "file", "manual")
        if row["verdict"] != "manual":
            assert row["evidence"], f"{row['id']} judges without evidence"
            assert row["whyManual"] is None
        else:
            assert row["checkKind"] == "manual"
            assert row["whyManual"]
            assert row["evidence"] == []
    assert "computed at request time" in body["honestyNote"]


def test_repo_root_checks_follow_visibility_honestly(client: TestClient) -> None:
    _, repo_root = default_roots()
    rows = rows_by_area(client.get(STACK_PATH).json())
    if repo_root is not None:
        assert rows["platform-services"]["checkKind"] == "file"
        assert rows["platform-services"]["verdict"] == "pass"
    else:
        assert rows["platform-services"]["verdict"] == "manual"
        assert "not visible from this process" in rows["platform-services"]["whyManual"]


def test_all_repo_root_rows_follow_the_same_direction(client: TestClient) -> None:
    _, repo_root = default_roots()
    rows = rows_by_area(client.get(STACK_PATH).json())
    for row_id in REPO_ROOT_ROW_IDS:
        if repo_root is not None:
            assert rows[row_id]["checkKind"] == "file", row_id
            assert rows[row_id]["verdict"] == "pass", row_id
            assert rows[row_id]["evidence"], row_id
        else:
            assert rows[row_id]["verdict"] == "manual", row_id
            assert "not visible from this process" in rows[row_id]["whyManual"]


def test_the_appconfig_row_verifies_in_every_environment(client: TestClient) -> None:
    """The parity row reads the SERVER tree — always mounted, always real."""
    rows = rows_by_area(client.get(STACK_PATH).json())
    config_row = rows["appconfig-fail-fast"]
    assert config_row["checkKind"] == "file"
    assert config_row["verdict"] == "pass"
    assert any("server tree" in line for line in config_row["evidence"])


def test_the_kubernetes_row_reports_an_honest_absence(client: TestClient) -> None:
    _, repo_root = default_roots()
    rows = rows_by_area(client.get(STACK_PATH).json())
    k8s = rows["k8s-manifests"]
    if repo_root is not None:
        assert k8s["verdict"] == "pass"
        assert any("does not exist" in line for line in k8s["evidence"])
    else:
        assert k8s["verdict"] == "manual"
    assert "No Kubernetes manifests" in k8s["claim"]


async def test_degraded_direction_without_the_repo_root(app: FastAPI) -> None:
    """No repo root at all: every repo-root row turns manual, nothing fakes."""
    server_root, _ = default_roots()
    payload = await build_deploy_stack_payload(
        app=app, config=get_config(), server_root=server_root, repo_root=None
    )
    rows = {row.id: row for area in payload.areas for row in area.items}
    for row_id in REPO_ROOT_ROW_IDS:
        assert rows[row_id].verdict == "manual", row_id
        assert "not visible from this process" in (rows[row_id].why_manual or "")
    # The runtime facts stay real, and the server-tree row still verifies.
    assert payload.runtime[-1].id == "health"
    assert payload.runtime[-1].value.startswith("200 {")
    assert rows["appconfig-fail-fast"].verdict == "pass"


async def test_a_broken_visible_tree_judges_fail_instead_of_crashing(
    app: FastAPI, tmp_path: Path
) -> None:
    """A VISIBLE but empty repo root: real checks that find nothing = fail."""
    payload = await build_deploy_stack_payload(
        app=app, config=get_config(), server_root=tmp_path, repo_root=tmp_path
    )
    rows = {row.id: row for area in payload.areas for row in area.items}
    assert rows["platform-services"].verdict == "fail"
    assert rows["image-rail"].verdict == "fail"
    assert "not found/readable" in rows["image-rail"].evidence[0]
    # An empty repo genuinely has no k8s manifests — the absence still verifies.
    assert rows["k8s-manifests"].verdict == "pass"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][STACK_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("DeployStackPanel")
