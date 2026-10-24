import { lazy, type ComponentType, type LazyExoticComponent } from 'react';

/**
 * Demo registry — the client-side half of the content API's demo-block
 * contract. Served content names a demo by the demo block's id; this record is
 * the only place that binds an id to an implementation. Demos are lazy-loaded
 * so a topic's chunk only pays for the demos it actually renders, and an
 * unknown id degrades to a "not wired yet" panel instead of crashing the
 * screen (see DemoHost).
 *
 * ── HOW A DEMO LANDS ────────────────────────────────────────────────────────
 * 1. Server side: a pure payload builder in `guide/domain/demos/` + a thin
 *    router at `guide/presentation/routers/demo/<area>.py` (area module), so
 *    the demo endpoint is `GET /api/demo/<area>/<name>` with a declared
 *    response model.
 * 2. Client data path: `src/domain/demo/<name>-repository.ts` (port) +
 *    `src/data/demo/<name>-{dto,api,repository-impl}.ts` + a use case in
 *    `src/domain/demo/`, wired in the container under its own tokens.
 * 3. Create `src/ui/demos/<area>/<name>_demo.tsx` — a DEFAULT-exported
 *    component taking no props (it resolves its own dependencies through the
 *    container, like every view) — with loading + error states and a
 *    fixture-driven spec (happy + failure).
 * 4. Add one entry here:
 *
 *      const MyDemo = lazy(() => import('./<area>/<name>_demo'));
 *      export const demoRegistry = { ..., '<area>:<name>': MyDemo };
 *
 * Nothing else changes: the content's demo-block id starts resolving through
 * DemoHost automatically. Demo ids follow the server's `<area>:<name>`
 * convention (e.g. `py:runtime-types`, `fastapi:app-info`).
 */

export type DemoComponentType = ComponentType;

export type DemoRegistry = Readonly<
  Record<string, LazyExoticComponent<DemoComponentType>>
>;

const RuntimeTypesDemo = lazy(() => import('./py/runtime_types_demo'));
const RuntimeAsyncDemo = lazy(() => import('./runtime/async_demo'));
const RuntimeStreamingDemo = lazy(() => import('./runtime/streaming_demo'));
const HttpHeadersDemo = lazy(() => import('./http/headers_demo'));
const FastApiAppInfoDemo = lazy(() => import('./fastapi/app_info_demo'));
const PydLabDemo = lazy(() => import('./pyd/lab_demo'));
const DepLifecycleDemo = lazy(() => import('./dep/lifecycle_demo'));
const DepMatrixDemo = lazy(() => import('./dep/matrix_demo'));
const RoutingExplorerDemo = lazy(() => import('./routing/explorer_demo'));
const MiddlewarePipelineDemo = lazy(() => import('./middleware/pipeline_demo'));
const ReqresInspectorDemo = lazy(() => import('./reqres/inspector_demo'));
const ReqresMethodsDemo = lazy(() => import('./reqres/methods_demo'));
const ValidationArenaDemo = lazy(() => import('./validation/arena_demo'));
const PostsWorkbenchDemo = lazy(() => import('./api/posts_workbench_demo'));
const DocsLinkDemo = lazy(() => import('./api/docs_link_demo'));
const GraphqlPlaygroundDemo = lazy(() => import('./api/graphql_playground_demo'));
const WebhookSimulatorDemo = lazy(() => import('./api/webhook_simulator_demo'));
const GrpcConsoleDemo = lazy(() => import('./api/grpc_console_demo'));
const SchemaExplorerDemo = lazy(() => import('./db/schema_explorer_demo'));
const UuidDemo = lazy(() => import('./db/uuid_demo'));
const SqlSafetyDemo = lazy(() => import('./db/sql_safety_demo'));
const DbMigrationsDemo = lazy(() => import('./db/migrations_demo'));
const SqlLabDemo = lazy(() => import('./db/sql_lab_demo'));
const DbSearchDemo = lazy(() => import('./db/search_demo'));
const DbRaceDemo = lazy(() => import('./db/race_demo'));
const DbAuditDemo = lazy(() => import('./db/audit_demo'));
const DbOrmProbeDemo = lazy(() => import('./db/orm_probe_demo'));
const MongoConsoleDemo = lazy(() => import('./db/mongo_console_demo'));
const RedisPlaygroundDemo = lazy(() => import('./redis/playground_demo'));
const CachingLabDemo = lazy(() => import('./caching/lab_demo'));
const MsgStreamDemo = lazy(() => import('./msg/stream_demo'));
const MsgOutboxDemo = lazy(() => import('./msg/outbox_demo'));
const AuthSessionsDemo = lazy(() => import('./auth/sessions_demo'));
const AuthApiKeysDemo = lazy(() => import('./auth/api_keys_demo'));
const AuthJwtDemo = lazy(() => import('./auth/jwt_demo'));
const AuthOauthDemo = lazy(() => import('./auth/oauth_demo'));
const AuthHashingDemo = lazy(() => import('./auth/hashing_demo'));
const AuthRefreshDemo = lazy(() => import('./auth/refresh_demo'));
const AuthzMatrixDemo = lazy(() => import('./authz/matrix_demo'));
const SecurityLabDemo = lazy(() => import('./security/lab_demo'));
const SecurityPiiDemo = lazy(() => import('./security/pii_demo'));
const FilesWorkbenchDemo = lazy(() => import('./files/workbench_demo'));
const I18nNegotiatorDemo = lazy(() => import('./i18n/negotiator_demo'));
const RealtimeTickerDemo = lazy(() => import('./realtime/ticker_demo'));
const RealtimeChatDemo = lazy(() => import('./realtime/chat_demo'));
const JobsConsoleDemo = lazy(() => import('./jobs/console_demo'));
const ErrorsExplorerDemo = lazy(() => import('./errors/explorer_demo'));
const DepsManifestDemo = lazy(() => import('./deps/manifest_demo'));
const ArchTracerDemo = lazy(() => import('./arch/tracer_demo'));
const ObsViewerDemo = lazy(() => import('./obs/viewer_demo'));
const ObsTraceDemo = lazy(() => import('./obs/trace_demo'));
const TestingRunnerDemo = lazy(() => import('./testing/runner_demo'));
const DebugStallDemo = lazy(() => import('./debug/stall_demo'));
const EnvInspectorDemo = lazy(() => import('./env/inspector_demo'));
const DeployStackDemo = lazy(() => import('./deploy/stack_demo'));
const PerfBenchDemo = lazy(() => import('./perf/bench_demo'));
const ReliabilityBreakerDemo = lazy(() => import('./reliability/breaker_demo'));
const ScalingStatelessDemo = lazy(() => import('./scaling/stateless_demo'));
const BestChecklistDemo = lazy(() => import('./best/checklist_demo'));

export const demoRegistry: DemoRegistry = {
  'py:runtime-types': RuntimeTypesDemo,
  'runtime:async': RuntimeAsyncDemo,
  'runtime:streaming': RuntimeStreamingDemo,
  'http:headers': HttpHeadersDemo,
  'fastapi:app-info': FastApiAppInfoDemo,
  'pyd:lab': PydLabDemo,
  'dep:lifecycle': DepLifecycleDemo,
  'dep:matrix': DepMatrixDemo,
  'routing:explorer': RoutingExplorerDemo,
  'middleware:pipeline': MiddlewarePipelineDemo,
  'reqres:inspector': ReqresInspectorDemo,
  'reqres:methods': ReqresMethodsDemo,
  'validation:arena': ValidationArenaDemo,
  'api:posts-workbench': PostsWorkbenchDemo,
  'api:docs-link': DocsLinkDemo,
  'api:graphql-playground': GraphqlPlaygroundDemo,
  'api:webhook-simulator': WebhookSimulatorDemo,
  'api:grpc-console': GrpcConsoleDemo,
  'db:schema-explorer': SchemaExplorerDemo,
  'db:uuid': UuidDemo,
  'db:sql-safety': SqlSafetyDemo,
  'db:migrations': DbMigrationsDemo,
  'db:sql-lab': SqlLabDemo,
  'db:search': DbSearchDemo,
  'db:race': DbRaceDemo,
  'db:audit': DbAuditDemo,
  'db:orm-probe': DbOrmProbeDemo,
  'db:mongo-console': MongoConsoleDemo,
  'redis:playground': RedisPlaygroundDemo,
  'caching:lab': CachingLabDemo,
  'msg:stream': MsgStreamDemo,
  'msg:outbox': MsgOutboxDemo,
  'auth:sessions': AuthSessionsDemo,
  'auth:api-keys': AuthApiKeysDemo,
  'auth:jwt': AuthJwtDemo,
  'auth:oauth': AuthOauthDemo,
  'auth:hashing': AuthHashingDemo,
  'auth:refresh': AuthRefreshDemo,
  'authz:matrix': AuthzMatrixDemo,
  'security:lab': SecurityLabDemo,
  'security:pii': SecurityPiiDemo,
  'files:workbench': FilesWorkbenchDemo,
  'i18n:negotiator': I18nNegotiatorDemo,
  'realtime:ticker': RealtimeTickerDemo,
  'realtime:chat': RealtimeChatDemo,
  'jobs:console': JobsConsoleDemo,
  'errors:explorer': ErrorsExplorerDemo,
  'deps:manifest': DepsManifestDemo,
  'arch:tracer': ArchTracerDemo,
  'obs:viewer': ObsViewerDemo,
  'obs:trace': ObsTraceDemo,
  'testing:runner': TestingRunnerDemo,
  'debug:stall': DebugStallDemo,
  'env:inspector': EnvInspectorDemo,
  'deploy:stack': DeployStackDemo,
  'perf:bench': PerfBenchDemo,
  'reliability:breaker': ReliabilityBreakerDemo,
  'scaling:stateless': ScalingStatelessDemo,
  'best:checklist': BestChecklistDemo,
};
