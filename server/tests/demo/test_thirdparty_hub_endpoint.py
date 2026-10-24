"""The thirdparty-hub endpoint (topic 42, area ``thirdparty``).

Pins the wire contract (GET /api/demo/thirdparty/hub): the eight-row
integrate-vs-build walk (every integrate row verified by a real tomllib
parse of the manifest at request time, every build row verified by its
module file existing in the server tree), the eight-row integration
inventory with each dependency's honest failure mode, the five-row
secrets panel — names, scopes, and blast radii only, proven value-free
by planting sentinel secrets and asserting they appear nowhere in the
serialized payload — and the five-row quotas panel (live reads beside
declared domain constants). Repo-root evidence is containment-checked
where the repo is mounted (tests + the dev container) and degrades to
an honest row when it is not, pinned by driving the builder directly.
"""

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from guide.core.config import get_config
from guide.domain.demos.thirdparty_hub import (
    LiveQuotaFacts,
    build_third_party_hub,
    default_roots,
)
from guide.main import create_app

HUB_PATH = "/api/demo/thirdparty/hub"

DECISION_ROW_IDS = [
    "graphql-engine",
    "password-hashing",
    "token-signing",
    "job-queue",
    "wire-drivers",
    "circuit-breaker",
    "webhook-signing",
    "oauth-provider",
]
INTEGRATION_ROW_IDS = [
    "postgres",
    "redis",
    "mongo",
    "arq-worker",
    "webhook-hmac",
    "oauth-provider",
    "ghcr-images",
    "caddy-edge",
]
SECRET_ROW_IDS = [
    "jwt-secret",
    "session-secret",
    "db-password",
    "webhook-shared-secret",
    "prod-env-concentrator",
]
QUOTA_ROW_IDS = [
    "rate-limit",
    "room-ceiling",
    "connection-queue",
    "upload-cap",
    "engine-pool",
]

PLANTED_JWT = "planted-jwt-sentinel-must-never-render"
PLANTED_SESSION = "planted-session-sentinel-must-never-render"


@pytest.fixture
def planted_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """An app booted with sentinel secrets — the redaction proof's ammunition."""
    monkeypatch.setenv("FDG_JWT_SECRET", PLANTED_JWT)
    monkeypatch.setenv("FDG_SESSION_SECRET", PLANTED_SESSION)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        yield client


def test_the_decision_walk_is_verified_against_the_manifest(client: TestClient) -> None:
    body = client.get(HUB_PATH).json()
    rows = body["decisions"]
    assert [row["id"] for row in rows] == DECISION_ROW_IDS
    choices = {row["id"]: row["choice"] for row in rows}
    assert all(choices[row] == "integrate" for row in DECISION_ROW_IDS[:5])
    assert all(choices[row] == "build" for row in DECISION_ROW_IDS[5:])
    by_id = {row["id"]: row for row in rows}
    # Integrate rows quote the requirement line a real tomllib parse found.
    assert "'strawberry-graphql[fastapi]>=0.335.0'" in by_id["graphql-engine"]["verified"]
    assert "server/pyproject.toml carries" in by_id["graphql-engine"]["verified"]
    assert "'argon2-cffi>=25.1.0'" in by_id["password-hashing"]["verified"]
    assert "'pyjwt>=2.15.1'" in by_id["token-signing"]["verified"]
    assert "'itsdangerous>=2.2.0'" in by_id["token-signing"]["verified"]
    assert "'arq>=0.25.0'" in by_id["job-queue"]["verified"]
    assert "'asyncpg>=0.32.0'" in by_id["wire-drivers"]["verified"]
    # Build rows name the module file this server tree actually carries.
    assert "guide/domain/reliability/breaker.py exists" in by_id["circuit-breaker"]["verified"]
    assert "guide/domain/webhooks/signing.py exists" in by_id["webhook-signing"]["verified"]
    assert "guide/domain/auth/oauth_service.py exists" in by_id["oauth-provider"]["verified"]
    # The reasons carry the decision's substance, not filler.
    assert "malpractice" in by_id["password-hashing"]["reason"]
    assert "identity provider" in by_id["oauth-provider"]["reason"]


def test_the_integration_inventory_names_every_real_surface(client: TestClient) -> None:
    body = client.get(HUB_PATH).json()
    rows = body["integrations"]
    assert [row["id"] for row in rows] == INTEGRATION_ROW_IDS
    by_id = {row["id"]: row for row in rows}
    assert by_id["postgres"]["kind"] == "backing-service"
    assert by_id["webhook-hmac"]["kind"] == "machine-auth"
    assert by_id["oauth-provider"]["kind"] == "auth-flow"
    assert by_id["ghcr-images"]["kind"] == "artifact"
    assert by_id["caddy-edge"]["kind"] == "edge"
    # The timeout/503 discipline is named where it applies.
    assert "two-second" in by_id["redis"]["detail"]
    assert "503" in by_id["redis"]["whenDown"]
    assert "503" in by_id["mongo"]["whenDown"]
    # The repo root is mounted in tests — the rails were containment-checked.
    assert "containment-checked" in by_id["ghcr-images"]["evidence"]
    assert "containment-checked" in by_id["caddy-edge"]["evidence"]
    assert "upstream.caddy" in by_id["caddy-edge"]["detail"]


def test_the_secrets_panel_is_value_free_by_construction(planted_client: TestClient) -> None:
    response = planted_client.get(HUB_PATH)
    assert response.status_code == 200
    raw = response.text
    # The planted sentinels booted this very app — and appear nowhere.
    assert PLANTED_JWT not in raw
    assert PLANTED_SESSION not in raw
    # Neither do the committed dev defaults the app would otherwise hold.
    assert "dev-only-jwt-secret" not in raw
    assert "dev-only-session-secret" not in raw
    body = json.loads(raw)
    rows = body["secrets"]
    assert [row["id"] for row in rows] == SECRET_ROW_IDS
    # No row carries a value field at all — names and radii only.
    assert all(set(row) == {"id", "envVar", "scope", "blastRadius", "handling", "evidence"}
               for row in rows)
    by_id = {row["id"]: row for row in rows}
    assert by_id["jwt-secret"]["envVar"] == "FDG_JWT_SECRET"
    assert "mints tokens for ANY user" in by_id["jwt-secret"]["blastRadius"]
    assert by_id["db-password"]["envVar"] == "FDG_DB_PASSWORD (inside FDG_DATABASE_URL)"
    assert "public by design" in by_id["webhook-shared-secret"]["blastRadius"]
    assert "never commit a webhook secret" in by_id["webhook-shared-secret"]["handling"]
    assert "PROD_ENV_B64" in by_id["prod-env-concentrator"]["envVar"]
    # The compose rails were containment-checked where the repo is mounted.
    assert "containment-checked" in by_id["db-password"]["evidence"]
    assert "server/.env.production.example" in by_id["prod-env-concentrator"]["evidence"]


def test_the_quota_rows_read_live_and_declared_numbers(client: TestClient) -> None:
    body = client.get(HUB_PATH).json()
    rows = body["quotas"]
    assert [row["id"] for row in rows] == QUOTA_ROW_IDS
    by_id = {row["id"]: row for row in rows}
    # Live reads: the limiter's policy and this app's engine pool.
    assert by_id["rate-limit"]["quota"] == "5 hits / 10s per client ip + route"
    assert by_id["rate-limit"]["source"] == "live"
    assert by_id["engine-pool"]["quota"] == "5 pooled connections per process"
    assert by_id["engine-pool"]["source"] == "live"
    # Declared constants: the realtime ceilings and the upload cap.
    assert by_id["room-ceiling"]["quota"] == "8 members per room"
    assert by_id["connection-queue"]["quota"] == "32 queued messages per connection"
    assert by_id["upload-cap"]["quota"] == "2 MiB per upload"
    assert by_id["room-ceiling"]["source"] == "constant"
    # Every ceiling names its behavior at the ceiling — policy, not a number.
    assert "429" in by_id["rate-limit"]["atCeiling"]
    assert "1013" in by_id["room-ceiling"]["atCeiling"]


def test_the_honesty_note_pins_the_vendor_rules(client: TestClient) -> None:
    note = client.get(HUB_PATH).json()["honestyNote"]
    assert "NOT dependencies" in note
    assert "never reads a secret" in note
    assert "sentinel values" in note


def test_the_panel_is_bounded(client: TestClient) -> None:
    response = client.get(HUB_PATH)
    assert response.elapsed.total_seconds() < 5.0, (
        "one manifest parse and some file stats — nothing sleeps, nothing dials out"
    )


def test_repo_root_rows_degrade_honestly_when_unmounted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without the repo root, the compose/env rows say so — never a fake check."""
    monkeypatch.setenv("FDG_JWT_SECRET", PLANTED_JWT)
    monkeypatch.setenv("FDG_SESSION_SECRET", PLANTED_SESSION)
    get_config.cache_clear()
    config = get_config()
    get_config.cache_clear()
    server_root, _ = default_roots()
    assert server_root.is_dir()
    panel = build_third_party_hub(
        server_root=server_root,
        repo_root=None,
        config=config,
        quotas=LiveQuotaFacts(rate_policy="5 hits / 10s per client ip + route", pool_size=5),
    )
    integrations = {row.id: row for row in panel.integrations}
    assert "not mounted" in integrations["ghcr-images"].evidence
    assert "not mounted" in integrations["caddy-edge"].evidence
    secrets = {row.id: row for row in panel.secrets}
    assert "not mounted" in secrets["db-password"].evidence
    # The server-tree rows verify everywhere — the manifest never left.
    decisions = {row.id: row for row in panel.decisions}
    assert "server/pyproject.toml carries" in decisions["graphql-engine"].verified
    assert "exists in this server tree" in decisions["circuit-breaker"].verified
    # And the degraded panel still carries no secret value.
    assert PLANTED_JWT not in panel.model_dump_json()


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][HUB_PATH]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert ref.endswith("ThirdPartyHubPanel")
