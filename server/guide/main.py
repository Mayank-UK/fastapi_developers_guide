"""Application entrypoint: the ``create_app()`` factory + module-level ``app``.

``create_app()`` builds a fully independent FastAPI instance (own routing
table, own DI container) — tests call it per case; the module-level ``app``
exists once per process for the ASGI entrypoint ``guide.main:app`` that the
Dockerfiles and compose run. This composition root wires, in order: logging,
per-app state (a fresh ScenarioStore and SpanLog per app; the production
content registry — already validated once at import, so broken content fails
the process at startup), the request-id middleware, the shared error
handlers, and every router. Routers stay thin; the posts resource is the
first real ports→adapters wiring (an in-memory adapter satisfies the
domain port — database adapters join from Phase 6 on), and topic 15 adds
the gRPC satellite: ONE runtime per app owning an in-process ``grpc.aio``
server (lazily started, ephemeral loopback port) plus the console adapter
behind the domain port — the lifespan's shutdown is what stops it. Topic
16 opens the data phase: per-app async engine + schema reader over the
config's database URL, and the lifespan's startup runs ``alembic upgrade
head`` best-effort (idempotent; a skipped migration with PostgreSQL down
logs a warning and the app still boots — the optional-service discipline).
Topic 19 adds the document store on the same deal: a lazy per-app motor
client over the config's mongo URL (construction connects to nothing),
with the console adapter behind the domain port — unreachable MongoDB
degrades the mongo demos to the service_unavailable envelope and the
app keeps serving everything else. Topic 20 closes the phase with the
in-memory store: a lazy per-app redis.asyncio client over the config's
redis URL (short socket timeouts, decode_responses), with the playground
adapter behind the domain port — unreachable Redis degrades the redis
demo the same way and the app keeps serving everything else. Topic 21
with that client to its most classic work the moment it exists: the
cache-aside service over the posts use cases, backed by a redis
``CacheStore`` adapter behind the domain port (unreachable Redis degrades
the caching lab the same way), plus the demo area's real conditional
endpoint. Topic 22 puts streams on the same client and a table in the
same PostgreSQL: the stream lab and the transactional-outbox relay over
the ``RedisStreams`` adapter (XADD/XREADGROUP/XACK/XPENDING/XAUTOCLAIM
plus the processed-set) and the ``PgOutboxStore`` adapter (the
one-transaction post+event write, the unpublished poll, the mark) —
unreachable stores degrade only the messaging labs. Topic 23 puts
IDENTENTITY on the stack: one in-memory auth state per app (seeded
users with pre-hashed argon2 credentials) satisfies all five auth store
ports, and six engines run over it — the session engine (itsdangerous-
sealed cookie), the API-key engine (SHA-256 at rest, constant-time
lookup), the HS256 token engine, the OAuth code+PKCE provider, the
argon2 password service, and the refresh-rotation engine with reuse
detection — all wired from the config's two signing secrets. Topic 24
layers the VERDICT over that identity: a pure policy engine over the
role→permission registry, a resolver that turns verified credentials
into authorization principals (roles from the registry, scopes from the
credential), a seeded comment ledger for the admin-only moderation
action, and the dependency guards (``require_permission`` /
``require_owner_or``) that make the two guarded endpoints thin. Topic 25
rounds the group into a security posture: a global security-headers
middleware (defensive headers on EVERY response, path-aware CSP for the
docs pages), Starlette's CORSMiddleware wired from topic 25's explicit
origin allow-list (credentials beside an exact list, never the wildcard),
the pure sliding-window rate limiter behind the dependency the burner
endpoint declares, and the seeded customer-record store the PII lab
classifies, masks by role, exports, and erases with counts as proof.
Topic 26 opens the media group: the files workbench service over its own
``FileStore`` port — uploads validated WHILE the body streams (cap +
magic-byte sniff agreement), stored under server-minted ids with the
user's name kept as data, served back with explicit Content-Disposition
(RFC 6266/5987 names) and RFC 9110 range windows, Pillow-derived
thumbnail/grayscale variants, and the paced async-generator stream that
makes backpressure visible. Topic 27 adds the language layer: the i18n
service over the repo's real gettext catalogs (compiled to .mo at import,
deterministically) — Accept-Language negotiation with visible fallbacks,
CLDR formatting through babel, category-math plurals, and zoneinfo wall
clocks for the negotiator demo. Topic 28 opens the realtime pair: the
shared ticker service (one deterministic simulated market every SSE
connection mints into, with a bounded replay ring for Last-Event-ID
resumption) and the chat room service over the in-process connection
manager (rooms, bounded per-connection queues, ceilings) — served by the
realtime router's event stream and websocket, with the demo router's two
panels shaping what they expose. The request-id middleware also becomes
pure ASGI here (its recorded BaseHTTPMiddleware caveat came due: SSE
must flow unbuffered and websocket scopes must carry the id too).
Topic 29 closes the group and the phase: the jobs console service over
the ArqJobs adapter (one lazily-created arq pool per app — enqueue,
key-layout lifecycle, the two queue numbers, and this namespace's own
trails/dead-letters/mailbox/heartbeat/ledger lists), the demo router's
twelve thin endpoints including the repo's REAL BackgroundTasks usage
(the comparison fires the same paced workload in-process and queued),
and a separate arq worker process (guide.worker, the compose arq-worker
service) whose tasks route every retry decision through the domain's
pure policy. Topic 30 opens the platform group with the error story as
the subject itself: the errors explorer panel (pure payload derived from
the taxonomy's own tables) and the probe — the scenario store's first
live failure-injection reader, the one endpoint whose failure is the
feature. Topic 32 turns the architecture inward as the subject: the
tracer demo that introspects the running app (the built stack, the
matched posts route's real dependency tree, the wiring behind the port)
and drives two REAL internal requests through the app at the ASGI
boundary — the Ok round crossing every layer, the Err round proving the
failure path end to end. Topic 34 points the lens at the suite itself:
the testing runner executes curated slices of the repo's own test files
in a subprocess — off the loop, hard-timeout'd, guarded against
recursion — so the tests that guard this app become a live exhibit of
the pyramid they form. Topic 36 turns the lens on the environment itself:
the env inspector serves one live read of the process's REAL config —
every setting with its true source, secrets redacted before the wire —
beside the scenario store's flag snapshot.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from guide import __version__
from guide.content.registry import production_registry
from guide.core.config import get_config
from guide.core.errors import register_exception_handlers
from guide.core.logging import configure_logging
from guide.core.request_context import RequestIdMiddleware
from guide.core.scenario import ScenarioStore
from guide.data.auth import InMemoryAuthState
from guide.data.caching import RedisCacheStore
from guide.data.db.engine import create_db_engine
from guide.data.db.introspection import PgSchemaReader
from guide.data.db.lifecycle import upgrade_database_on_startup
from guide.data.db.orm import OrmProbeRepository, create_session_factory
from guide.data.db.repository import PgGuideRepository
from guide.data.grpc.console import InProcessGrpcConsole
from guide.data.grpc.runtime import GrpcRuntime
from guide.data.jobs import ArqJobs, create_arq_pool_factory
from guide.data.messaging import PgOutboxStore, RedisStreams
from guide.data.mongo import MongoConsoleRepository, create_mongo_client
from guide.data.posts.in_memory import InMemoryPostRepository
from guide.data.redis import RedisPlaygroundRepository, create_redis_client
from guide.data.scaling import RedisSharedCounter
from guide.domain.auth.api_key_service import ApiKeyService
from guide.domain.auth.jwt_service import TokenService
from guide.domain.auth.oauth_service import OAuthProviderService
from guide.domain.auth.password_service import PasswordService, production_hasher
from guide.domain.auth.refresh_service import RefreshRotationService
from guide.domain.auth.session_service import SessionService
from guide.domain.authz.comments import CommentLedger
from guide.domain.authz.engine import PolicyEngine
from guide.domain.authz.principals import PrincipalResolver
from guide.domain.caching.service import CacheAsidePostsService
from guide.domain.demos.demo_reset import build_demo_reset_service
from guide.domain.demos.request_methods import NoteStore
from guide.domain.files.service import FilesWorkbenchService
from guide.domain.files.storage import InMemoryFileStore
from guide.domain.i18n.catalog import MessageCatalog
from guide.domain.i18n.service import I18nService
from guide.domain.jobs.service import JobsConsoleService
from guide.domain.messaging.outbox_service import OutboxRelayService
from guide.domain.messaging.stream_service import StreamLabService
from guide.domain.posts.ports import PostRepository
from guide.domain.posts.use_cases import (
    CreatePostUseCase,
    GetPostUseCase,
    ListPostsUseCase,
    PostUseCases,
    ReplacePostUseCase,
)
from guide.domain.realtime.chat import ChatRoomService
from guide.domain.realtime.manager import ConnectionManager
from guide.domain.realtime.ticker import TickerService
from guide.domain.security.cors import (
    ALLOW_CREDENTIALS,
    ALLOWED_HEADERS,
    ALLOWED_METHODS,
    ALLOWED_ORIGINS,
    PREFLIGHT_MAX_AGE_S,
)
from guide.domain.security.rate_limit import DEMO_POLICY, SlidingWindowLimiter
from guide.domain.security.records import CustomerRecordStore
from guide.presentation.dependencies.request_span import SpanLog
from guide.presentation.middleware.request_log import RequestLogMiddleware
from guide.presentation.middleware.security_headers import SecurityHeadersMiddleware
from guide.presentation.routers import content, graphql, health, posts, realtime
from guide.presentation.routers.demo import api as demo_api
from guide.presentation.routers.demo import arch as demo_arch
from guide.presentation.routers.demo import auth as demo_auth
from guide.presentation.routers.demo import authz as demo_authz
from guide.presentation.routers.demo import best as demo_best
from guide.presentation.routers.demo import caching as demo_caching
from guide.presentation.routers.demo import db as demo_db
from guide.presentation.routers.demo import debug as demo_debug
from guide.presentation.routers.demo import dep as demo_dep
from guide.presentation.routers.demo import deploy as demo_deploy
from guide.presentation.routers.demo import deps as demo_deps
from guide.presentation.routers.demo import env as demo_env
from guide.presentation.routers.demo import errors as demo_errors
from guide.presentation.routers.demo import fastapi as demo_fastapi
from guide.presentation.routers.demo import files as demo_files
from guide.presentation.routers.demo import http as demo_http
from guide.presentation.routers.demo import i18n as demo_i18n
from guide.presentation.routers.demo import jobs as demo_jobs
from guide.presentation.routers.demo import middleware as demo_middleware
from guide.presentation.routers.demo import msg as demo_msg
from guide.presentation.routers.demo import obs as demo_obs
from guide.presentation.routers.demo import perf as demo_perf
from guide.presentation.routers.demo import py as demo_py
from guide.presentation.routers.demo import pyd as demo_pyd
from guide.presentation.routers.demo import realtime as demo_realtime
from guide.presentation.routers.demo import redis as demo_redis
from guide.presentation.routers.demo import reliability as demo_reliability
from guide.presentation.routers.demo import reqres as demo_reqres
from guide.presentation.routers.demo import reset as demo_reset
from guide.presentation.routers.demo import routing as demo_routing
from guide.presentation.routers.demo import runtime as demo_runtime
from guide.presentation.routers.demo import scaling as demo_scaling
from guide.presentation.routers.demo import scenario as demo_scenario
from guide.presentation.routers.demo import security as demo_security
from guide.presentation.routers.demo import testing as demo_testing
from guide.presentation.routers.demo import thirdparty as demo_thirdparty
from guide.presentation.routers.demo import validation as demo_validation

APP_TITLE: Final = "FastAPI Developers Guide"

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Migrations up at startup (best-effort), connections down at shutdown.

    ``alembic upgrade head`` is idempotent — an up-to-date database costs
    one version-table read — and a failed attempt (PostgreSQL down) logs
    a warning instead of killing the boot, per the optional-service
    discipline. Shutdown disposes the async engine (no-op when unused)
    and stops the gRPC satellite if it ever started (also a no-op when
    unused).
    """
    config = get_config()
    await upgrade_database_on_startup(config.database_url)
    yield
    await app.state.db_engine.dispose()
    await app.state.grpc_runtime.stop()
    app.state.mongo_client.close()
    await app.state.redis_client.aclose()


def create_app() -> FastAPI:
    """Build one wired FastAPI application instance."""
    config = get_config()
    configure_logging(config.log_level)
    app = FastAPI(title=APP_TITLE, version=__version__, lifespan=lifespan)

    app.state.scenario = ScenarioStore()
    app.state.span_log = SpanLog()
    app.state.content_registry = production_registry
    app.state.reqres_notes = NoteStore()

    # The posts resource: the composition root decides WHICH adapter
    # satisfies the domain port — in-memory today, a database from Phase 6
    # on — and wires the use cases over it once, per app (tests get
    # per-app isolation; the routers never learn the adapter's name).
    posts_repository: PostRepository = InMemoryPostRepository()
    app.state.posts_repository = posts_repository
    posts_use_cases = PostUseCases(
        list_posts=ListPostsUseCase(posts_repository),
        get_post=GetPostUseCase(posts_repository),
        create_post=CreatePostUseCase(posts_repository),
        replace_post=ReplacePostUseCase(posts_repository),
    )
    app.state.posts_use_cases = posts_use_cases

    # The gRPC satellite (topic 15): the SAME posts use cases, served as
    # guide.PostService by an in-process grpc.aio server. The runtime owns
    # server + channel lifecycle (lazy start, ephemeral port); the console
    # adapter behind the domain port is the only shape routers see.
    grpc_runtime = GrpcRuntime(posts_use_cases)
    app.state.grpc_runtime = grpc_runtime
    app.state.grpc_console = InProcessGrpcConsole(grpc_runtime)

    # The data phase (topic 16 on): ONE async engine per app over the
    # config's database URL (lazy — construction connects to nothing, so
    # the app boots with PostgreSQL down), the schema reader the explorer
    # demo resolves, and the query repository behind topic 17's six
    # live-SQL demos (seed, safety probe, migration rehearsal, lab
    # exhibits, search, race, audit proof). Topic 18 adds the ORM half
    # beside the engine: the async session factory (units of work over
    # the same pool) and the probe runner behind the orm-probe demo.
    db_engine = create_db_engine(config)
    app.state.db_engine = db_engine
    app.state.schema_reader = PgSchemaReader(db_engine)
    app.state.guide_repository = PgGuideRepository(db_engine)
    orm_sessions = create_session_factory(db_engine)
    app.state.orm_session_factory = orm_sessions
    app.state.orm_probe = OrmProbeRepository(db_engine, orm_sessions)

    # The document store (topic 19): ONE lazy motor client per app over
    # the config's mongo URL — construction connects to nothing, so the
    # app boots with MongoDB down and only the mongo demos degrade (to
    # the service_unavailable envelope). The console adapter behind the
    # domain port owns every pymongo/motor import; routers never see it.
    mongo_client = create_mongo_client(config)
    app.state.mongo_client = mongo_client
    app.state.mongo_console = MongoConsoleRepository(mongo_client)

    # The in-memory store (topic 20): ONE lazy redis.asyncio client per app
    # over the config's redis URL — construction connects to nothing, so the
    # app boots with Redis down and only the redis demo degrades (to the
    # service_unavailable envelope). Short socket timeouts keep that
    # degradation fast; the playground adapter behind the domain port owns
    # every redis-py import; routers never see it.
    redis_client = create_redis_client(config)
    app.state.redis_client = redis_client
    app.state.redis_playground = RedisPlaygroundRepository(redis_client)

    # Topic 40's shared counter: the same redis client behind the smallest
    # port that can prove where state lives — two "replicas" increment ONE
    # key, and the second answer contains the first's write because the
    # value lives in the store, not in either process. Unreachable Redis
    # degrades only the scaling demo (service_unavailable envelope).
    app.state.shared_counter = RedisSharedCounter(redis_client)

    # Topic 21's cache-aside lab over the SAME posts use cases /api/posts
    # serves: the domain service owns keys, TTL, single-flight, and
    # telemetry; the store adapter owns every redis-py import over the
    # shared client above. One service per app keeps the counters
    # process-local and coherent; unreachable Redis degrades only the
    # caching lab (service_unavailable envelope).
    app.state.caching_service = CacheAsidePostsService(
        posts_use_cases, RedisCacheStore(redis_client)
    )

    # Topic 22's messaging labs: the stream lab (consumer-group lifecycle
    # over the shared redis client) and the transactional-outbox relay
    # (the SAME redis client for publishes and the SAME async engine above
    # for the outbox table — one transaction, post + event, in PostgreSQL).
    # The RedisStreams adapter satisfies all three stream-shaped ports;
    # unreachable stores degrade only these labs, never the app.
    streams = RedisStreams(redis_client)
    app.state.stream_lab = StreamLabService(streams, streams)
    app.state.outbox_service = OutboxRelayService(
        PgOutboxStore(db_engine), streams, streams, streams
    )

    # Topic 23's authentication labs: ONE in-memory auth state per app
    # (seeded users, sessions, keys, codes, refresh families — per-app
    # isolation for free, no external store to degrade) satisfies every
    # auth store port; six engines run over it. The two signing secrets
    # come from the config's dev-only defaults (production overrides via
    # env — AppConfig's startup validator makes forgetting that a boot
    # failure outside dev).
    auth_state = InMemoryAuthState()
    app.state.auth_state = auth_state
    passwords = PasswordService(production_hasher())
    app.state.auth_passwords = passwords
    app.state.auth_sessions = SessionService(
        auth_state, auth_state, passwords, config.session_secret
    )
    app.state.auth_api_keys = ApiKeyService(auth_state)
    app.state.auth_tokens = TokenService(config.jwt_secret, auth_state, passwords)
    app.state.auth_oauth = OAuthProviderService(auth_state, app.state.auth_tokens)
    app.state.auth_refresh = RefreshRotationService(
        auth_state, auth_state, passwords, app.state.auth_tokens
    )

    # Topic 24's authorization lab: the verdict layer over the identity the
    # auth state established — the pure policy engine (registry-backed,
    # stateless), the resolver that turns verified credentials into principals
    # (roles from the registry, scopes from the credential), and the seeded
    # comment ledger the admin-only moderation action acts on. The guards
    # live in presentation/dependencies/authz.py; routers stay thin.
    app.state.authz_engine = PolicyEngine()
    app.state.authz_resolver = PrincipalResolver(auth_state)
    app.state.authz_comments = CommentLedger()

    # Topic 25's security substrate: the per-app rate limiter (the pure
    # sliding window, clock injected — the burner endpoint's dependency
    # reads it) and the PII lab's seeded record store (synthetic customers
    # only; masking/erasure run over it, and POST /pii/reset reseeds).
    app.state.rate_limiter = SlidingWindowLimiter(DEMO_POLICY)
    app.state.pii_records = CustomerRecordStore()

    # Topic 26's media substrate: the workbench service over the files port
    # — the in-memory adapter is demo-scoped BY DECLARATION (a restart loses
    # the store; the panel says so), and the port is the seam a disk or S3
    # adapter fills without touching the service.
    app.state.files_workbench = FilesWorkbenchService(InMemoryFileStore())

    # Topic 27's i18n substrate: the negotiator service over the repo's real
    # compiled catalogs — .po files under domain/i18n/locales compiled to .mo
    # at import (deterministic), served through stdlib gettext with the
    # fallback chain, beside the pure negotiation/formatting/zone engines.
    app.state.i18n_service = I18nService(MessageCatalog())

    # Topic 28's realtime substrate: ONE shared ticker per app (every SSE
    # connection mints into the same deterministic sequence, so any client's
    # Last-Event-ID is meaningful to the next) and ONE chat manager + room
    # service (rooms of bounded-queue members — process-local by design, the
    # panel says so). The routers stay thin; the protocols' framing and
    # ceiling decisions live in the domain.
    app.state.ticker_service = TickerService()
    app.state.chat_service = ChatRoomService(ConnectionManager())

    # Topic 29's jobs substrate: the console service over the ArqJobs
    # adapter and ONE lazily-created arq pool (the optional-service
    # discipline — the app boots with Redis down; only the jobs demo
    # degrades to the service_unavailable envelope). The WORKER half
    # lives in guide.worker, booted by the compose arq-worker service
    # over the same redis, the same catalog, the same policy.
    app.state.jobs_service = JobsConsoleService(ArqJobs(create_arq_pool_factory(config)))

    # The shared demo reset (Phase 12): every participant over the reset
    # path it ALREADY owns — the scenario store, the caching lab's
    # invalidation, the shared counter's delete, the jobs console's reset,
    # the PII store's reseed, the log ring's clear. The posts reseed is the
    # one place the composition root reaches past the port on purpose: the
    # adapter's reset-to-seed is a demo affordance the RESOURCE port
    # deliberately does not carry, so the guard below re-establishes the
    # concrete type the wiring itself just built.
    if not isinstance(posts_repository, InMemoryPostRepository):
        raise RuntimeError(
            "the demo reset's posts participant needs the in-memory adapter"
        )
    app.state.demo_reset_service = build_demo_reset_service(
        scenario=app.state.scenario,
        reset_posts=posts_repository.reset,
        counter=app.state.shared_counter,
        caching=app.state.caching_service,
        jobs=app.state.jobs_service,
        pii_records=app.state.pii_records,
    )

    # Middleware stack (added innermost-first): request ids innermost, the
    # security headers stamping EVERY response (error envelopes included),
    # CORS outermost so even inner error responses carry the CORS verdict —
    # the browser must be able to READ a 429 or a 500 envelope cross-origin.
    # The CORS policy is topic 25's explicit origin allow-list; credentials
    # ride beside it, never beside a wildcard (the classic misconfig).
    app.add_middleware(RequestIdMiddleware)
    # Topic 33's access-log layer wraps the request-id layer: it reads the
    # id RequestIdMiddleware stamps on the response and logs one structured
    # http_request event per request — the whole onion timed end to end.
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=ALLOW_CREDENTIALS,
        allow_methods=list(ALLOWED_METHODS),
        allow_headers=list(ALLOWED_HEADERS),
        max_age=PREFLIGHT_MAX_AGE_S,
    )
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(content.router)
    app.include_router(posts.router)
    # The GraphQL mount: resolvers over the SAME posts use cases the REST
    # router serves — one URL (POST /api/graphql), excluded from OpenAPI
    # because the query language has no OpenAPI shape; the SDL is the contract.
    app.include_router(graphql.router)
    app.include_router(demo_scenario.router)
    app.include_router(demo_py.router)
    app.include_router(demo_pyd.router)
    app.include_router(demo_runtime.router)
    app.include_router(demo_http.router)
    app.include_router(demo_fastapi.router)
    app.include_router(demo_routing.router)
    app.include_router(demo_dep.router)
    app.include_router(demo_middleware.router)
    app.include_router(demo_reqres.router)
    app.include_router(demo_validation.router)
    app.include_router(demo_api.router)
    app.include_router(demo_db.router)
    app.include_router(demo_redis.router)
    app.include_router(demo_caching.router)
    app.include_router(demo_msg.router)
    app.include_router(demo_auth.router)
    app.include_router(demo_authz.router)
    app.include_router(demo_security.router)
    app.include_router(demo_files.router)
    app.include_router(demo_i18n.router)
    # The realtime pair: the live SSE stream + websocket (real substrate),
    # then the demo panels that describe them.
    app.include_router(realtime.router)
    app.include_router(demo_realtime.router)
    # The jobs pair: the console demo endpoints (the live queue is the
    # substrate — the enqueues and polls ARE the real thing).
    app.include_router(demo_jobs.router)
    # Topic 30's errors explorer: the panel is pure payload, and the probe
    # is the scenario store's first live failure-injection reader — the
    # one endpoint whose FAILURE is the feature.
    app.include_router(demo_errors.router)
    # Topic 31's deps manifest: the REAL pyproject.toml + uv.lock parsed at
    # request time — groups, locked pins vs manifest ranges, drift, and the
    # direct-vs-transitive tree the uv tree/audit section teaches.
    app.include_router(demo_deps.router)
    # Topic 32's architecture tracer: introspects the running app and
    # drives two REAL internal requests through it — the layers and the
    # wiring made visible in one payload.
    app.include_router(demo_arch.router)
    # Topic 33's observability demos: the structured-log viewer (the real
    # structlog pipeline introspected + the process's recent-event ring)
    # and the trace fan-out (three REAL internal rounds correlated by
    # request id across header, envelope, and log row).
    app.include_router(demo_obs.router)
    # Topic 34's testing runner: executes curated slices of the repo's own
    # test suite in a subprocess (off the loop, hard timeout, recursion
    # guard) — the suite that guards this app becomes a live exhibit.
    app.include_router(demo_testing.router)
    # Topic 35's stall diagnosis: four bounded phases (an async await, a
    # threadpool-contained block, an on-loop block, a baseline) each with
    # real instruments — elapsed, loop-lag probe, a concurrent REAL
    # /api/health, a tracemalloc window, and this request's correlated
    # log rows. The profiling evidence py-spy would sample from outside,
    # measured from inside, without wedging the shared loop.
    app.include_router(demo_debug.router)
    # Topic 36's env inspector: one live read of the REAL AppConfig — every
    # setting with its true source (env or default), secrets redacted
    # server-side before the payload exists, plus the scenario store's flag
    # snapshot beside it.
    app.include_router(demo_env.router)
    # Topic 37's deploy stack: inspects the repo's REAL deploy surface —
    # the compose trio's services and rails, the Dockerfiles' stages, the
    # CI/deploy workflows' gates, the env template — plus the runtime
    # facts this process always has (env, command line, a REAL internal
    # /api/health). Repo-root checks degrade to honest manual rows on the
    # live server container, whose bind mount is server/ only.
    app.include_router(demo_deploy.router)
    # Topic 38's performance bench: every row measured on the request —
    # real gzip over the bytes this API actually serves, the on-loop vs
    # threadpool hygiene comparison with live probes, uvicorn's
    # auto-selected loop/parser introspected, the engine pool's counters,
    # and the stdlib GC read plus one off-loop measured collection.
    app.include_router(demo_perf.router)
    # Topic 39's circuit breaker: one GET walking the real pure substrate
    # (domain/reliability/breaker.py) through a full cycle per request —
    # closed → open → half-open → closed, every verdict and latency real,
    # the open timeout elapsing on an injected clock.
    app.include_router(demo_reliability.router)
    # Topic 40's statelessness panel: the state-placement lesson by
    # introspection — the router snapshots the composition root's real
    # in-process facts, and the builder walks one logical request through
    # two per-replica state worlds: a process-local write that never
    # crosses, beside a real redis INCR that does.
    app.include_router(demo_scaling.router)
    # Topic 41's best-practices checklist: a live self-audit — real probes
    # through this very app, real repo reads, honest manual verdicts where
    # no automation can judge.
    app.include_router(demo_best.router)
    # Topic 42's third-party hub: the integrate-vs-build walk verified
    # against the manifest and the server tree at request time, the real
    # integration inventory, the key/secret surface as names (never
    # values), and the live quotas — the panel the third-party topic
    # teaches around, degraded honestly where the repo root is not
    # mounted.
    app.include_router(demo_thirdparty.router)
    # Phase 12's shared demo reset: the terminal companion's one-call
    # return-to-baseline over every demo state's existing reset path.
    app.include_router(demo_reset.router)
    return app


app: Final = create_app()
