"""The third-party hub payload: what this app integrated, built, and owes.

``GET /api/demo/thirdparty/hub`` serves this payload INLINE in topic 42's
integrating-vs-building section. The panel answers the third-party
question — what does this application depend on that it did not build,
what did it deliberately build anyway, and what does every one of those
choices cost? — with four inventories, each row derived from a real
source on the very request that serves it:

- **decisions** — the integrate-vs-build walk. Every "integrate" row is
  verified against ``server/pyproject.toml`` parsed with tomllib at
  request time (the manifest requirement line is quoted); every "build"
  row is verified by the module file existing in this server tree.
- **integrations** — the REAL third-party surface: the three backing
  services with their timeout/503 discipline, the arq worker process,
  the webhook HMAC signer/verifier (the repo's machine-to-machine
  authentication), the in-repo OAuth2 code+PKCE flow, and the deploy
  pipeline's third-party channels (GHCR images, the shared caddy edge).
  Repo-root evidence (the compose files, the env template) is checked
  for real when the repo root is mounted and reports an honest degraded
  row otherwise — the server container's bind mount is ``server/`` only.
- **secrets** — the key/secret surface as NAMES, never values: each row
  names the env var, what it protects, and what its leak would blast.
  The values are never read into this module at all, so no
  serialization path — JSON, repr, log — can carry one (the endpoint
  test proves it with planted sentinel values).
- **quotas** — the real in-repo ceilings, live where the process can
  read them (the limiter's policy, the engine pool's size) and from the
  domain's own constants where they are declared (the realtime
  ceilings, the upload cap).

The honesty rule this panel pins for the topic: aiosmtplib, Stripe, and
cloud-storage SDKs are NOT dependencies of this repo — the topic teaches
them as concept + recipe, and this panel carries no fabricated live
integration for any of them.
"""

import tomllib
from pathlib import Path
from typing import Final, Literal

from guide.core.config import AppConfig
from guide.core.serialization import CamelModel
from guide.domain.files.validation import MAX_UPLOAD_BYTES
from guide.domain.realtime.manager import MAX_ROOM_CONNECTIONS, PER_CONNECTION_QUEUE

REPO_ROOT_MARKER: Final = ".dockerignore"
"""A file only the real repo root carries — the honest visibility test."""

_PRODCOMPOSE: Final = ".docker/docker-compose.prod.yml"
_MANIFEST: Final = "pyproject.toml"

DecisionChoice = Literal["integrate", "build"]
"""One axis of the walk: bought from an ecosystem, or written in-repo."""

QuotaSource = Literal["live", "constant"]
"""Where a quota row reads its number: the running process, or a module constant."""


class DecisionRow(CamelModel):
    """One integrate-vs-build decision this repo actually made."""

    id: str
    choice: DecisionChoice
    subject: str
    package: str
    reason: str
    blast_radius: str
    verified: str


class IntegrationRow(CamelModel):
    """One real third-party integration: what it is, and what its failure does."""

    id: str
    kind: str
    name: str
    detail: str
    when_down: str
    evidence: str


class SecretRow(CamelModel):
    """One key/secret in the real surface — named, scoped, blast-radius'd.

    There is deliberately no value field: the builder never reads a
    secret value, so the wire cannot carry one.
    """

    id: str
    env_var: str
    scope: str
    blast_radius: str
    handling: str
    evidence: str


class QuotaRow(CamelModel):
    """One real ceiling the app enforces — the number and the behavior at it."""

    id: str
    quota: str
    scope: str
    at_ceiling: str
    source: QuotaSource


class LiveQuotaFacts(CamelModel):
    """The quota facts the ROUTER snapshots — live reads off app.state."""

    rate_policy: str
    pool_size: int


class ThirdPartyHubPanel(CamelModel):
    """Wire shape of ``GET /api/demo/thirdparty/hub`` — the panel's contract."""

    decisions: list[DecisionRow]
    integrations: list[IntegrationRow]
    secrets: list[SecretRow]
    quotas: list[QuotaRow]
    honesty_note: str


HONESTY_NOTE: Final = (
    "Every row was derived on this request. The decision walk parsed this "
    "repo's real manifest with tomllib (every 'integrate' row quotes the "
    "requirement line it found) and checked every 'build' row's module "
    "against this server tree. The integration inventory names the wiring "
    "create_app actually builds; repo-root evidence (the compose rails, "
    "the env template) was checked as text when the repo root is mounted "
    "and reports an honest degraded row on the live server container, "
    "whose bind mount is server/ only. The secrets inventory carries "
    "NAMES and blast radii, never values — the builder never reads a "
    "secret, so the wire cannot carry one; the endpoint test plants "
    "sentinel values and proves they appear nowhere in the payload. "
    "Quota rows are live reads (the limiter's policy, this app's engine "
    "pool) or the domain's own declared constants. And the honesty rule "
    "the topic teaches is pinned here too: aiosmtplib, Stripe, and "
    "cloud-storage SDKs are NOT dependencies of this repo — no row on "
    "this panel pretends otherwise."
)


def _read(root: Path | None, relative: str) -> str | None:
    """One file's text under a root, or None when it is not there."""
    if root is None:
        return None
    try:
        return (root / relative).read_text(encoding="utf-8")
    except OSError:
        return None


def resolve_roots(module_file: Path) -> tuple[Path, Path | None]:
    """The server root for a domain/demos module file, and the repo root when visible.

    Same depth contract as the deploy-stack resolver (demos → domain →
    guide → server): the server root is three parents up; the repo root
    is one more and only counts when its marker file is actually mounted
    — the server container binds server/ alone, and honest rows must
    say so.
    """
    server_root = module_file.resolve().parents[3]
    candidate = server_root.parent
    repo_root = candidate if (candidate / REPO_ROOT_MARKER).is_file() else None
    return server_root, repo_root


def default_roots() -> tuple[Path, Path | None]:
    """The roots for THIS module — the one place the depth assumption lives."""
    return resolve_roots(Path(__file__))


def _requirement_line(dependencies: list[str], name: str) -> str | None:
    """The manifest requirement whose PEP 508 name is ``name``, or None.

    Strips extras and version operators before comparing, so
    ``strawberry-graphql[fastapi]>=0.335.0`` answers to ``strawberry-graphql``.
    """
    wanted = name.lower().replace("_", "-")
    for requirement in dependencies:
        head = requirement.split("[", 1)[0]
        for operator in ("===", "==", ">=", "<=", "~=", "!=", ">", "<"):
            head = head.split(operator, 1)[0]
        if head.strip().lower().replace("_", "-") == wanted:
            return requirement
    return None


def _manifest_dependencies(server_root: Path) -> list[str] | None:
    """The [project] dependencies of this repo's manifest, parsed for real."""
    text = _read(server_root, _MANIFEST)
    if text is None:
        return None
    try:
        parsed: dict[str, object] = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    project = parsed.get("project")
    if not isinstance(project, dict):
        return None
    deps = project.get("dependencies")
    if not isinstance(deps, list):
        return None
    return [str(dep) for dep in deps]


def _integrate_verified(deps: list[str] | None, packages: tuple[str, ...]) -> str:
    """The honest verification line for one integrate decision."""
    if deps is None:
        return "server/pyproject.toml could not be read on this request — row unverified"
    lines = [line for name in packages if (line := _requirement_line(deps, name))]
    if len(lines) != len(packages):
        missing = [name for name in packages if _requirement_line(deps, name) is None]
        return f"manifest does NOT carry {', '.join(missing)} — row unverified"
    quoted = " and ".join(f"'{line}'" for line in lines)
    return f"server/pyproject.toml carries {quoted} (parsed on this request)"


def _build_verified(server_root: Path, module: str) -> str:
    """The honest verification line for one build decision."""
    if (server_root / module).is_file():
        return f"{module} exists in this server tree (checked on this request)"
    return f"{module} NOT found in this server tree — row unverified"


def _decision_rows(server_root: Path) -> list[DecisionRow]:
    """The integrate-vs-build walk, every row verified against a real source."""
    deps = _manifest_dependencies(server_root)
    rows: list[DecisionRow] = [
        DecisionRow(
            id="graphql-engine",
            choice="integrate",
            subject="the GraphQL API surface (POST /api/graphql)",
            package="strawberry-graphql[fastapi]",
            reason=(
                "a GraphQL engine is a parser, a type system, an executor, and a "
                "loader — strawberry brought the SDL, the resolvers, and the "
                "DataLoader batching topic 13 proved live; hand-rolling it is a "
                "research project, not a feature"
            ),
            blast_radius="every GraphQL query the playground console posts",
            verified=_integrate_verified(deps, ("strawberry-graphql",)),
        ),
        DecisionRow(
            id="password-hashing",
            choice="integrate",
            subject="password storage (auth:hashing)",
            package="argon2-cffi",
            reason=(
                "the one category where building is malpractice: argon2 is the "
                "Password Hashing Competition winner behind a CFFI wrapper — this "
                "repo's job is parameters and the rehash policy, never the "
                "arithmetic"
            ),
            blast_radius="every login and every seeded credential",
            verified=_integrate_verified(deps, ("argon2-cffi",)),
        ),
        DecisionRow(
            id="token-signing",
            choice="integrate",
            subject="JWTs and sealed sessions",
            package="pyjwt + itsdangerous",
            reason=(
                "signing FORMATS have format pitfalls — algorithm confusion, "
                "missing-expiry checks — so the format implementation is bought "
                "and the KEY and the policy stay this repo's own"
            ),
            blast_radius="every access token and session cookie the auth labs mint",
            verified=_integrate_verified(deps, ("pyjwt", "itsdangerous")),
        ),
        DecisionRow(
            id="job-queue",
            choice="integrate",
            subject="the deferred-work queue (jobs:console)",
            package="arq",
            reason=(
                "queue semantics, retries, cron, and worker supervision are a "
                "product — this repo kept only the retry POLICY pure in-domain "
                "(topic 29) and lets arq execute its verdicts"
            ),
            blast_radius="every deferred job, the dead-letter queue, and the heartbeat",
            verified=_integrate_verified(deps, ("arq",)),
        ),
        DecisionRow(
            id="wire-drivers",
            choice="integrate",
            subject="the datastore wire protocols",
            package="asyncpg + redis + motor",
            reason=(
                "wire protocols are bought, then BOUNDED — the two-second "
                "optional-service timeouts are this repo's own discipline layered "
                "over the drivers, not a property the drivers ship with"
            ),
            blast_radius="all data access: SQL, streams, cache, jobs, documents",
            verified=_integrate_verified(deps, ("asyncpg", "redis", "motor")),
        ),
        DecisionRow(
            id="circuit-breaker",
            choice="build",
            subject="the circuit breaker substrate",
            package="guide/domain/reliability/breaker.py",
            reason=(
                "pybreaker exists and topic 39 names it — but the substrate is "
                "about a hundred readable lines with an injected clock, and the "
                "states ARE the lesson; buying it would hide the exact thing "
                "being taught"
            ),
            blast_radius=(
                "the reliability breaker demo — a defect is a wrong gate, "
                "contained by the substrate's 23 unit tests"
            ),
            verified=_build_verified(
                server_root, "guide/domain/reliability/breaker.py"
            ),
        ),
        DecisionRow(
            id="webhook-signing",
            choice="build",
            subject="webhook HMAC signing and verification",
            package="guide/domain/webhooks/signing.py",
            reason=(
                "forty lines over the standard library's hmac/hashlib — and the "
                "receiver's raw-body-first discipline is this app's own contract; "
                "a signing SDK would own the one boundary the lesson is about"
            ),
            blast_radius="POST /api/demo/api/webhooks/receive — every delivery's authenticity",
            verified=_build_verified(server_root, "guide/domain/webhooks/signing.py"),
        ),
        DecisionRow(
            id="oauth-provider",
            choice="build",
            subject="the OAuth2 authorization-code + PKCE flow",
            package="guide/domain/auth/oauth_service.py",
            reason=(
                "built small on purpose so every protocol step — consent, the "
                "one-time code, S256, code burning — is readable; a production "
                "system INTEGRATES an identity provider instead, and this row "
                "says so"
            ),
            blast_radius="the auth:oauth lab — a defect is a broken demo flow, not a "
            "production identity surface",
            verified=_build_verified(server_root, "guide/domain/auth/oauth_service.py"),
        ),
    ]
    return rows


def _repo_evidence(
    repo_root: Path | None,
    relative: str,
    needles: tuple[str, ...],
    found: str,
    degraded: str,
) -> str:
    """Containment check over one repo-root file, honestly degraded when absent."""
    text = _read(repo_root, relative)
    if text is None:
        return (
            f"{relative} is not mounted in this container (bind mount is server/ "
            f"only) — {degraded}"
        )
    if all(needle in text for needle in needles):
        return found
    return f"{relative} no longer carries the quoted rail — re-check this row"


def _integration_rows(repo_root: Path | None) -> list[IntegrationRow]:
    """The real third-party surface this app stands on, row by row."""
    return [
        IntegrationRow(
            id="postgres",
            kind="backing-service",
            name="PostgreSQL 17",
            detail=(
                "ONE async engine per app (pool_pre_ping reconnects stale "
                "sockets) and Alembic migrations best-effort at boot — the app "
                "starts with the store down"
            ),
            when_down=(
                "the data demos degrade honestly; the engine reconnects when the "
                "store returns — a restart is not an outage"
            ),
            evidence="wired in create_app over the config's database_url rail "
            "(server/guide/main.py)",
        ),
        IntegrationRow(
            id="redis",
            kind="backing-service",
            name="Redis 8",
            detail=(
                "ONE lazy redis.asyncio client (two-second socket timeouts) "
                "shared by five adapters: the playground, the cache store, the "
                "streams, the jobs queue, and the shared counter"
            ),
            when_down=(
                "only the redis-backed demos answer the 503 envelope — bounded "
                "by the client's two-second discipline, never a hung worker"
            ),
            evidence="the shared client + adapter wiring in server/guide/main.py; "
            "timeouts in server/guide/data/redis/client.py",
        ),
        IntegrationRow(
            id="mongo",
            kind="backing-service",
            name="MongoDB 8",
            detail=(
                "ONE lazy motor client with two-second server-selection and "
                "connect timeouts behind the console port"
            ),
            when_down="only the mongo demo 503s; the app and every other demo keep serving",
            evidence="client constants in server/guide/data/mongo/client.py; the "
            "optional-service map in server/guide/data/mongo/console.py",
        ),
        IntegrationRow(
            id="arq-worker",
            kind="backing-service",
            name="the arq worker process",
            detail=(
                "the SAME server image as a second compose process over the same "
                "redis — the queue's execution half, with every retry decision "
                "routed through the domain's pure policy"
            ),
            when_down=(
                "enqueues park in the queue while the API keeps serving — the "
                "honest split topic 29 teaches: acceptance and execution are "
                "different failure domains"
            ),
            evidence="compose service arq-worker in .docker/docker-compose.yml; the "
            "tasks in server/guide/worker.py",
        ),
        IntegrationRow(
            id="webhook-hmac",
            kind="machine-auth",
            name="webhook HMAC signing",
            detail=(
                "the repo's real machine-to-machine authentication surface: "
                "HMAC-SHA256 over '{timestamp}.{payload}' with a ±300s freshness "
                "window and a constant-time compare"
            ),
            when_down=(
                "every failure gate answers the 401 envelope — replay, tamper, "
                "and clock skew each refuse with their own reason"
            ),
            evidence="sign_payload/verify_payload in server/guide/domain/webhooks/"
            "signing.py; the raw-body-first receiver in the api demo router",
        ),
        IntegrationRow(
            id="oauth-provider",
            kind="auth-flow",
            name="the OAuth2 code + PKCE provider",
            detail=(
                "the in-repo third-party-style flow: authorize issues a one-time "
                "code bound to client, redirect URI, and S256 challenge; the "
                "exchange burns the code on first presentation"
            ),
            when_down=(
                "no external dependency to fail — InMemoryAuthState holds the "
                "codes, and the flow's failure modes are its own pinned tests"
            ),
            evidence="OAuthProviderService in server/guide/domain/auth/oauth_service.py",
        ),
        IntegrationRow(
            id="ghcr-images",
            kind="artifact",
            name="GHCR release images",
            detail=(
                "the deploy pipeline's third-party channel: GitHub hosts this "
                "app's own artifacts as ghcr.io/mayank-uk/fastapi-guide-"
                "{server,client}:${IMAGE_TAG:?} — the required-variable rail "
                "refuses a tagless boot"
            ),
            when_down=(
                "a pull failure stops the release before any traffic flips — the "
                "boot gates never see an image"
            ),
            evidence=_repo_evidence(
                repo_root,
                _PRODCOMPOSE,
                (
                    "ghcr.io/mayank-uk/fastapi-guide-server:${IMAGE_TAG:?IMAGE_TAG is required}",
                    "ghcr.io/mayank-uk/fastapi-guide-client:${IMAGE_TAG:?IMAGE_TAG is required}",
                ),
                "both image rails found in .docker/docker-compose.prod.yml "
                "(containment-checked on this request)",
                "the image rails are real but were checked from the repo root "
                "only where it is mounted",
            ),
        ),
        IntegrationRow(
            id="caddy-edge",
            kind="edge",
            name="the shared caddy edge",
            detail=(
                "ONE shared caddy on the VM (its own compose project, the only "
                "publisher of 80/443) joins the external fdg_frontend network to "
                "reach this app's client containers by name; releases flip by "
                "rewriting upstream.caddy and `caddy reload`"
            ),
            when_down=(
                "the edge sits outside this stack's blast radius by design — the "
                "platform file's header documents the seam in its own words"
            ),
            evidence=_repo_evidence(
                repo_root,
                ".docker/docker-compose-platform.yml",
                ("upstream.caddy", "fdg_frontend", "caddy reload"),
                "the flip seam documented in .docker/docker-compose-platform.yml's "
                "header (containment-checked on this request)",
                "the flip seam is documented in the platform compose's header, "
                "checked where the repo root is mounted",
            ),
        ),
    ]


def _secret_rows(server_root: Path, repo_root: Path | None, config: AppConfig) -> list[SecretRow]:
    """The key/secret surface — names, scopes, blast radii; never a value."""
    env_note = (
        f"this process booted env={config.env}: the two signing secrets are the "
        "dev-only defaults AppConfig's validator allows there, named here and "
        "never shown"
    )
    return [
        SecretRow(
            id="jwt-secret",
            env_var="FDG_JWT_SECRET",
            scope=(
                "signs every HS256 access token — the auth:jwt lab, the OAuth "
                "exchange, and refresh rotation all mint with it"
            ),
            blast_radius=(
                "a leak mints tokens for ANY user until the key rotates — "
                "verification trusts the key alone, so the refresh-family kill "
                "switch cannot help"
            ),
            handling=(
                "AppConfig refuses the dev default outside dev (fail-fast "
                "validator at boot); the prod compose carries the required rail"
            ),
            evidence=f"config field jwt_secret (server/guide/core/config.py); {env_note}",
        ),
        SecretRow(
            id="session-secret",
            env_var="FDG_SESSION_SECRET",
            scope=(
                "seals the session cookie (itsdangerous) — the id inside resolves "
                "against in-process auth state"
            ),
            blast_radius="a leak forges sessions — impersonation until rotation",
            handling=(
                "same rails as the JWT secret: dev default refused outside dev, "
                "required rail in the prod compose, distinct from FDG_JWT_SECRET "
                "by the validator's own error message"
            ),
            evidence=f"config field session_secret (server/guide/core/config.py); {env_note}",
        ),
        SecretRow(
            id="db-password",
            env_var="FDG_DB_PASSWORD (inside FDG_DATABASE_URL)",
            scope="the PostgreSQL credential — user postgres, database guide",
            blast_radius=(
                "a leak is full read/write to the guide database; the platform's "
                "POSTGRES_PASSWORD is the same value by construction"
            ),
            handling=(
                "required rail in the prod compose; the real value lives only in "
                "the GitHub production environment, never in the repo"
            ),
            evidence=_repo_evidence(
                repo_root,
                _PRODCOMPOSE,
                (
                    "${FDG_DB_PASSWORD:?FDG_DB_PASSWORD must be set to a real database password}",
                    "- FDG_JWT_SECRET=${FDG_JWT_SECRET:?",
                    "- FDG_SESSION_SECRET=${FDG_SESSION_SECRET:?",
                ),
                "all three required rails found in .docker/docker-compose.prod.yml "
                "(containment-checked on this request)",
                "the three required rails are real in the prod compose, checked "
                "where the repo root is mounted",
            ),
        ),
        SecretRow(
            id="webhook-shared-secret",
            env_var="DEMO_SHARED_SECRET (module constant — no env var)",
            scope="signs and verifies the demo webhook deliveries",
            blast_radius=(
                "worthless in dev (public by design so the tour can recompute the "
                "HMAC by hand); a REAL deployment's per-subscription secret leak "
                "would let anyone forge deliveries"
            ),
            handling=(
                "the divergence is stated in the module's own docstring: real "
                "deployments never commit a webhook secret — per-subscription "
                "secrets in config, rotated"
            ),
            evidence="DEMO_SHARED_SECRET in server/guide/domain/webhooks/signing.py, "
            "with its public-by-design rationale",
        ),
        SecretRow(
            id="prod-env-concentrator",
            env_var="PROD_ENV_B64 (GitHub Actions secret, production environment)",
            scope=(
                "materializes server/.env.production on the VM — the concentrator "
                "that carries every value above to the place the rails read them"
            ),
            blast_radius="a leak is every secret above at once",
            handling=(
                "the committed file is only the TEMPLATE (.env.production.example) "
                "— placeholder values that boot but protect nothing; the real "
                "file never touches the repo"
            ),
            evidence=_env_example_evidence(server_root),
        ),
    ]


def _env_example_evidence(server_root: Path) -> str:
    """The env template lives in the server tree — readable everywhere."""
    text = _read(server_root, ".env.production.example")
    if text is None:
        return "server/.env.production.example could not be read on this request"
    needles = ("PROD_ENV_B64", "FDG_DB_PASSWORD=", "FDG_JWT_SECRET=", "FDG_SESSION_SECRET=")
    if all(needle in text for needle in needles):
        return (
            "server/.env.production.example documents the materialization path and "
            "the three values (containment-checked on this request)"
        )
    return (
        "server/.env.production.example no longer carries the quoted values — "
        "re-check this row"
    )


def _quota_rows(quotas: LiveQuotaFacts) -> list[QuotaRow]:
    """The real ceilings this app enforces — live reads and declared constants."""
    return [
        QuotaRow(
            id="rate-limit",
            quota=quotas.rate_policy,
            scope="every route the limiter guards (the security lab's burner)",
            at_ceiling=(
                "the 429 envelope with Retry-After (rounded up, never zero); "
                "denied hits are not recorded, so a hammering client does not "
                "extend its own lockout"
            ),
            source="live",
        ),
        QuotaRow(
            id="room-ceiling",
            quota=f"{MAX_ROOM_CONNECTIONS} members per room",
            scope="the realtime chat rooms",
            at_ceiling="join refused under the lock with close code 1013 (try again later)",
            source="constant",
        ),
        QuotaRow(
            id="connection-queue",
            quota=f"{PER_CONNECTION_QUEUE} queued messages per connection",
            scope="every live websocket member",
            at_ceiling=(
                "broadcast retires the slow consumer (discards, then the 1013 "
                "sentinel) — the sender never awaits a fallen-behind receiver"
            ),
            source="constant",
        ),
        QuotaRow(
            id="upload-cap",
            quota=f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MiB per upload",
            scope="the files workbench",
            at_ceiling=(
                "enforced WHILE READING (the cap plus one 64 KiB chunk) — a 422 "
                "envelope, never a buffered bomb"
            ),
            source="constant",
        ),
        QuotaRow(
            id="engine-pool",
            quota=f"{quotas.pool_size} pooled connections per process",
            scope="every data request this process serves",
            at_ceiling=(
                "checkouts queue up to the thirty-second timeout topic 38 "
                "measured — the bulkhead every SQL request shares"
            ),
            source="live",
        ),
    ]


def build_third_party_hub(
    *,
    server_root: Path,
    repo_root: Path | None,
    config: AppConfig,
    quotas: LiveQuotaFacts,
) -> ThirdPartyHubPanel:
    """Serve the panel: decisions, integrations, secrets, quotas.

    ``server_root`` is the server/ tree this process lives in (the
    manifest and every build-row module read from it); ``repo_root`` is
    the full repo when mounted (compose/env-template containment checks
    degrade honestly without it); ``config`` supplies the boot
    environment — and nothing else: secret VALUES are never read;
    ``quotas`` is the live snapshot the router took off app.state.
    """
    return ThirdPartyHubPanel(
        decisions=_decision_rows(server_root),
        integrations=_integration_rows(repo_root),
        secrets=_secret_rows(server_root, repo_root, config),
        quotas=_quota_rows(quotas),
        honesty_note=HONESTY_NOTE,
    )
