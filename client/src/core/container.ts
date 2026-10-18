import { type AppConfig } from './config/app-config';
import { ContentApi } from '../data/content/content-api';
import { ContentRepositoryImpl } from '../data/content/content-repository-impl';
import type { ContentRepository } from '../domain/content/content-repository';
import { ListContentUseCase } from '../domain/content/list-content-usecase';
import { GetTopicDetailUseCase } from '../domain/content/get-topic-detail-usecase';
import { HealthApi } from '../data/health/health-api';
import { HealthRepositoryImpl } from '../data/health/health-repository-impl';
import type { HealthRepository } from '../domain/health/health-repository';
import { GetHealthUseCase } from '../domain/health/get-health-usecase';
import { RuntimeTypesApi } from '../data/demo/runtime-types-api';
import { RuntimeTypesRepositoryImpl } from '../data/demo/runtime-types-repository-impl';
import type { RuntimeTypesRepository } from '../domain/demo/runtime-types-repository';
import { GetRuntimeTypesDemoUseCase } from '../domain/demo/get-runtime-types-demo-usecase';
import { RuntimeAsyncApi } from '../data/demo/runtime-async-api';
import { RuntimeAsyncRepositoryImpl } from '../data/demo/runtime-async-repository-impl';
import type { RuntimeAsyncRepository } from '../domain/demo/runtime-async-repository';
import { GetRuntimeAsyncDemoUseCase } from '../domain/demo/get-runtime-async-demo-usecase';
import { RuntimeStreamingApi } from '../data/demo/runtime-streaming-api';
import { RuntimeStreamingRepositoryImpl } from '../data/demo/runtime-streaming-repository-impl';
import type { RuntimeStreamingRepository } from '../domain/demo/runtime-streaming-repository';
import { GetRuntimeStreamingDemoUseCase } from '../domain/demo/get-runtime-streaming-demo-usecase';
import { HttpHeadersApi } from '../data/demo/http-headers-api';
import { HttpHeadersRepositoryImpl } from '../data/demo/http-headers-repository-impl';
import type { HttpHeadersRepository } from '../domain/demo/http-headers-repository';
import { GetHttpHeadersDemoUseCase } from '../domain/demo/get-http-headers-demo-usecase';
import { FastApiAppInfoApi } from '../data/demo/fastapi-app-info-api';
import { FastApiAppInfoRepositoryImpl } from '../data/demo/fastapi-app-info-repository-impl';
import type { FastApiAppInfoRepository } from '../domain/demo/fastapi-app-info-repository';
import { GetFastApiAppInfoDemoUseCase } from '../domain/demo/get-fastapi-app-info-demo-usecase';
import { PydLabApi } from '../data/demo/pyd-lab-api';
import { PydLabRepositoryImpl } from '../data/demo/pyd-lab-repository-impl';
import type { PydLabRepository } from '../domain/demo/pyd-lab-repository';
import { GetPydLabDemoUseCase } from '../domain/demo/get-pyd-lab-demo-usecase';
import { DepLifecycleApi } from '../data/demo/dep-lifecycle-api';
import { DepLifecycleRepositoryImpl } from '../data/demo/dep-lifecycle-repository-impl';
import type { DepLifecycleRepository } from '../domain/demo/dep-lifecycle-repository';
import { GetDepLifecycleDemoUseCase } from '../domain/demo/get-dep-lifecycle-demo-usecase';
import { DepMatrixApi } from '../data/demo/dep-matrix-api';
import { DepMatrixRepositoryImpl } from '../data/demo/dep-matrix-repository-impl';
import type { DepMatrixRepository } from '../domain/demo/dep-matrix-repository';
import { GetDepMatrixDemoUseCase } from '../domain/demo/get-dep-matrix-demo-usecase';
import { RoutingExplorerApi } from '../data/demo/routing-explorer-api';
import { RoutingExplorerRepositoryImpl } from '../data/demo/routing-explorer-repository-impl';
import type { RoutingExplorerRepository } from '../domain/demo/routing-explorer-repository';
import { GetRoutingExplorerDemoUseCase } from '../domain/demo/get-routing-explorer-demo-usecase';
import { MiddlewarePipelineApi } from '../data/demo/middleware-pipeline-api';
import { MiddlewarePipelineRepositoryImpl } from '../data/demo/middleware-pipeline-repository-impl';
import type { MiddlewarePipelineRepository } from '../domain/demo/middleware-pipeline-repository';
import { GetMiddlewarePipelineDemoUseCase } from '../domain/demo/get-middleware-pipeline-demo-usecase';
import { ReqresInspectorApi } from '../data/demo/reqres-inspector-api';
import { ReqresInspectorRepositoryImpl } from '../data/demo/reqres-inspector-repository-impl';
import type { ReqresInspectorRepository } from '../domain/demo/reqres-inspector-repository';
import { GetReqresInspectorDemoUseCase } from '../domain/demo/get-reqres-inspector-demo-usecase';
import { ReqresMethodsApi } from '../data/demo/reqres-methods-api';
import { ReqresMethodsRepositoryImpl } from '../data/demo/reqres-methods-repository-impl';
import type { ReqresMethodsRepository } from '../domain/demo/reqres-methods-repository';
import { ReqresMethodsDemoUseCase } from '../domain/demo/reqres-methods-demo-usecase';
import { ValidationArenaApi } from '../data/demo/validation-arena-api';
import { ValidationArenaRepositoryImpl } from '../data/demo/validation-arena-repository-impl';
import type { ValidationArenaRepository } from '../domain/demo/validation-arena-repository';
import { GetValidationArenaDemoUseCase } from '../domain/demo/get-validation-arena-demo-usecase';
import { PostsWorkbenchApi } from '../data/demo/posts-workbench-api';
import { PostsWorkbenchRepositoryImpl } from '../data/demo/posts-workbench-repository-impl';
import type { PostsWorkbenchRepository } from '../domain/demo/posts-workbench-repository';
import { GetPostsWorkbenchDemoUseCase } from '../domain/demo/get-posts-workbench-demo-usecase';
import { DocsLinkApi } from '../data/demo/docs-link-api';
import { DocsLinkRepositoryImpl } from '../data/demo/docs-link-repository-impl';
import type { DocsLinkRepository } from '../domain/demo/docs-link-repository';
import { GetDocsLinkDemoUseCase } from '../domain/demo/get-docs-link-demo-usecase';
import { GraphqlPlaygroundApi } from '../data/demo/graphql-playground-api';
import { GraphqlPlaygroundRepositoryImpl } from '../data/demo/graphql-playground-repository-impl';
import type { GraphqlPlaygroundRepository } from '../domain/demo/graphql-playground-repository';
import { GetGraphqlPlaygroundDemoUseCase } from '../domain/demo/get-graphql-playground-demo-usecase';
import { WebhookSimulatorApi } from '../data/demo/webhook-simulator-api';
import { WebhookSimulatorRepositoryImpl } from '../data/demo/webhook-simulator-repository-impl';
import type { WebhookSimulatorRepository } from '../domain/demo/webhook-simulator-repository';
import { GetWebhookSimulatorDemoUseCase } from '../domain/demo/get-webhook-simulator-demo-usecase';
import { GrpcConsoleApi } from '../data/demo/grpc-console-api';
import { GrpcConsoleRepositoryImpl } from '../data/demo/grpc-console-repository-impl';
import type { GrpcConsoleRepository } from '../domain/demo/grpc-console-repository';
import { GetGrpcConsoleDemoUseCase } from '../domain/demo/get-grpc-console-demo-usecase';
import { SchemaExplorerApi } from '../data/demo/schema-explorer-api';
import { SchemaExplorerRepositoryImpl } from '../data/demo/schema-explorer-repository-impl';
import type { SchemaExplorerRepository } from '../domain/demo/schema-explorer-repository';
import { GetSchemaExplorerDemoUseCase } from '../domain/demo/get-schema-explorer-demo-usecase';
import { UuidLabApi } from '../data/demo/uuid-lab-api';
import { UuidLabRepositoryImpl } from '../data/demo/uuid-lab-repository-impl';
import type { UuidLabRepository } from '../domain/demo/uuid-lab-repository';
import { GetUuidLabDemoUseCase } from '../domain/demo/get-uuid-lab-demo-usecase';
import { SqlSafetyApi } from '../data/demo/sql-safety-api';
import { SqlSafetyRepositoryImpl } from '../data/demo/sql-safety-repository-impl';
import type { SqlSafetyRepository } from '../domain/demo/sql-safety-repository';
import { GetSqlSafetyDemoUseCase } from '../domain/demo/get-sql-safety-demo-usecase';
import { DbMigrationsApi } from '../data/demo/db-migrations-api';
import { DbMigrationsRepositoryImpl } from '../data/demo/db-migrations-repository-impl';
import type { DbMigrationsRepository } from '../domain/demo/db-migrations-repository';
import { GetDbMigrationsDemoUseCase } from '../domain/demo/get-db-migrations-demo-usecase';
import { SqlLabApi } from '../data/demo/sql-lab-api';
import { SqlLabRepositoryImpl } from '../data/demo/sql-lab-repository-impl';
import type { SqlLabRepository } from '../domain/demo/sql-lab-repository';
import { GetSqlLabDemoUseCase } from '../domain/demo/get-sql-lab-demo-usecase';
import { DbSearchApi } from '../data/demo/db-search-api';
import { DbSearchRepositoryImpl } from '../data/demo/db-search-repository-impl';
import type { DbSearchRepository } from '../domain/demo/db-search-repository';
import { GetDbSearchDemoUseCase } from '../domain/demo/get-db-search-demo-usecase';
import { DbRaceApi } from '../data/demo/db-race-api';
import { DbRaceRepositoryImpl } from '../data/demo/db-race-repository-impl';
import type { DbRaceRepository } from '../domain/demo/db-race-repository';
import { GetDbRaceDemoUseCase } from '../domain/demo/get-db-race-demo-usecase';
import { DbAuditApi } from '../data/demo/db-audit-api';
import { DbAuditRepositoryImpl } from '../data/demo/db-audit-repository-impl';
import type { DbAuditRepository } from '../domain/demo/db-audit-repository';
import { GetDbAuditDemoUseCase } from '../domain/demo/get-db-audit-demo-usecase';
import { DbOrmProbeApi } from '../data/demo/db-orm-probe-api';
import { DbOrmProbeRepositoryImpl } from '../data/demo/db-orm-probe-repository-impl';
import type { DbOrmProbeRepository } from '../domain/demo/db-orm-probe-repository';
import { GetDbOrmProbeDemoUseCase } from '../domain/demo/get-db-orm-probe-demo-usecase';
import { MongoConsoleApi } from '../data/demo/mongo-console-api';
import { MongoConsoleRepositoryImpl } from '../data/demo/mongo-console-repository-impl';
import type { MongoConsoleRepository } from '../domain/demo/mongo-console-repository';
import { GetMongoConsoleDemoUseCase } from '../domain/demo/get-mongo-console-demo-usecase';
import { RedisPlaygroundApi } from '../data/demo/redis-playground-api';
import { RedisPlaygroundRepositoryImpl } from '../data/demo/redis-playground-repository-impl';
import type { RedisPlaygroundRepository } from '../domain/demo/redis-playground-repository';
import { GetRedisPlaygroundDemoUseCase } from '../domain/demo/get-redis-playground-demo-usecase';
import { CachingLabApi } from '../data/demo/caching-lab-api';
import { CachingLabRepositoryImpl } from '../data/demo/caching-lab-repository-impl';
import type { CachingLabRepository } from '../domain/demo/caching-lab-repository';
import { GetCachingLabDemoUseCase } from '../domain/demo/get-caching-lab-demo-usecase';
import { MsgStreamApi } from '../data/demo/msg-stream-api';
import { MsgStreamRepositoryImpl } from '../data/demo/msg-stream-repository-impl';
import type { MsgStreamRepository } from '../domain/demo/msg-stream-repository';
import { GetMsgStreamDemoUseCase } from '../domain/demo/get-msg-stream-demo-usecase';
import { MsgOutboxApi } from '../data/demo/msg-outbox-api';
import { MsgOutboxRepositoryImpl } from '../data/demo/msg-outbox-repository-impl';
import type { MsgOutboxRepository } from '../domain/demo/msg-outbox-repository';
import { GetMsgOutboxDemoUseCase } from '../domain/demo/get-msg-outbox-demo-usecase';
import { AuthSessionsApi } from '../data/demo/auth-sessions-api';
import { AuthSessionsRepositoryImpl } from '../data/demo/auth-sessions-repository-impl';
import type { AuthSessionsRepository } from '../domain/demo/auth-sessions-repository';
import { GetAuthSessionsDemoUseCase } from '../domain/demo/get-auth-sessions-demo-usecase';
import { AuthApiKeysApi } from '../data/demo/auth-api-keys-api';
import { AuthApiKeysRepositoryImpl } from '../data/demo/auth-api-keys-repository-impl';
import type { AuthApiKeysRepository } from '../domain/demo/auth-api-keys-repository';
import { GetAuthApiKeysDemoUseCase } from '../domain/demo/get-auth-api-keys-demo-usecase';
import { AuthJwtApi } from '../data/demo/auth-jwt-api';
import { AuthJwtRepositoryImpl } from '../data/demo/auth-jwt-repository-impl';
import type { AuthJwtRepository } from '../domain/demo/auth-jwt-repository';
import { GetAuthJwtDemoUseCase } from '../domain/demo/get-auth-jwt-demo-usecase';
import { AuthOauthApi } from '../data/demo/auth-oauth-api';
import { AuthOauthRepositoryImpl } from '../data/demo/auth-oauth-repository-impl';
import type { AuthOauthRepository } from '../domain/demo/auth-oauth-repository';
import { GetAuthOauthDemoUseCase } from '../domain/demo/get-auth-oauth-demo-usecase';
import { AuthHashingApi } from '../data/demo/auth-hashing-api';
import { AuthHashingRepositoryImpl } from '../data/demo/auth-hashing-repository-impl';
import type { AuthHashingRepository } from '../domain/demo/auth-hashing-repository';
import { GetAuthHashingDemoUseCase } from '../domain/demo/get-auth-hashing-demo-usecase';
import { AuthRefreshApi } from '../data/demo/auth-refresh-api';
import { AuthRefreshRepositoryImpl } from '../data/demo/auth-refresh-repository-impl';
import type { AuthRefreshRepository } from '../domain/demo/auth-refresh-repository';
import { GetAuthRefreshDemoUseCase } from '../domain/demo/get-auth-refresh-demo-usecase';
import { AuthzMatrixApi } from '../data/demo/authz-matrix-api';
import { AuthzMatrixRepositoryImpl } from '../data/demo/authz-matrix-repository-impl';
import type { AuthzMatrixRepository } from '../domain/demo/authz-matrix-repository';
import { GetAuthzMatrixDemoUseCase } from '../domain/demo/get-authz-matrix-demo-usecase';
import { SecurityLabApi } from '../data/demo/security-lab-api';
import { SecurityLabRepositoryImpl } from '../data/demo/security-lab-repository-impl';
import type { SecurityLabRepository } from '../domain/demo/security-lab-repository';
import { GetSecurityLabDemoUseCase } from '../domain/demo/get-security-lab-demo-usecase';
import { SecurityPiiApi } from '../data/demo/security-pii-api';
import { SecurityPiiRepositoryImpl } from '../data/demo/security-pii-repository-impl';
import type { SecurityPiiRepository } from '../domain/demo/security-pii-repository';
import { GetSecurityPiiDemoUseCase } from '../domain/demo/get-security-pii-demo-usecase';
import { FilesWorkbenchApi } from '../data/demo/files-workbench-api';
import { FilesWorkbenchRepositoryImpl } from '../data/demo/files-workbench-repository-impl';
import type { FilesWorkbenchRepository } from '../domain/demo/files-workbench-repository';
import { GetFilesWorkbenchDemoUseCase } from '../domain/demo/get-files-workbench-demo-usecase';
import { I18nNegotiatorApi } from '../data/demo/i18n-negotiator-api';
import { I18nNegotiatorRepositoryImpl } from '../data/demo/i18n-negotiator-repository-impl';
import type { I18nNegotiatorRepository } from '../domain/demo/i18n-negotiator-repository';
import { GetI18nNegotiatorDemoUseCase } from '../domain/demo/get-i18n-negotiator-demo-usecase';
import { RealtimeTickerApi } from '../data/demo/realtime-ticker-api';
import { RealtimeTickerRepositoryImpl } from '../data/demo/realtime-ticker-repository-impl';
import type { RealtimeTickerRepository } from '../domain/demo/realtime-ticker-repository';
import { GetRealtimeTickerDemoUseCase } from '../domain/demo/get-realtime-ticker-demo-usecase';
import { RealtimeChatApi } from '../data/demo/realtime-chat-api';
import { RealtimeChatRepositoryImpl } from '../data/demo/realtime-chat-repository-impl';
import type { RealtimeChatRepository } from '../domain/demo/realtime-chat-repository';
import { GetRealtimeChatDemoUseCase } from '../domain/demo/get-realtime-chat-demo-usecase';
import { JobsConsoleApi } from '../data/demo/jobs-console-api';
import { JobsConsoleRepositoryImpl } from '../data/demo/jobs-console-repository-impl';
import type { JobsConsoleRepository } from '../domain/demo/jobs-console-repository';
import { GetJobsConsoleDemoUseCase } from '../domain/demo/get-jobs-console-demo-usecase';
import { ErrorsExplorerApi } from '../data/demo/errors-explorer-api';
import { ErrorsExplorerRepositoryImpl } from '../data/demo/errors-explorer-repository-impl';
import type { ErrorsExplorerRepository } from '../domain/demo/errors-explorer-repository';
import { GetErrorsExplorerDemoUseCase } from '../domain/demo/get-errors-explorer-demo-usecase';
import { ArchTracerApi } from '../data/demo/arch-tracer-api';
import { ArchTracerRepositoryImpl } from '../data/demo/arch-tracer-repository-impl';
import { TestingRunnerApi } from '../data/demo/testing-runner-api';
import { TestingRunnerRepositoryImpl } from '../data/demo/testing-runner-repository-impl';
import type { ArchTracerRepository } from '../domain/demo/arch-tracer-repository';
import { GetArchTracerDemoUseCase } from '../domain/demo/get-arch-tracer-demo-usecase';
import type { TestingRunnerRepository } from '../domain/demo/testing-runner-repository';
import { GetTestingRunnerDemoUseCase } from '../domain/demo/get-testing-runner-demo-usecase';
import { EnvInspectorApi } from '../data/demo/env-inspector-api';
import { EnvInspectorRepositoryImpl } from '../data/demo/env-inspector-repository-impl';
import type { EnvInspectorRepository } from '../domain/demo/env-inspector-repository';
import { GetEnvInspectorDemoUseCase } from '../domain/demo/get-env-inspector-demo-usecase';
import { BestChecklistApi } from '../data/demo/best-checklist-api';
import { BestChecklistRepositoryImpl } from '../data/demo/best-checklist-repository-impl';
import type { BestChecklistRepository } from '../domain/demo/best-checklist-repository';
import { GetBestChecklistDemoUseCase } from '../domain/demo/get-best-checklist-demo-usecase';

/**
 * Service-locator container — this client's composition root, mirroring the
 * express/spring guides' `container.ts`. A small hand-rolled locator:
 * `register` singletons keyed by symbol, `resolve` them. It keeps wiring in
 * one explicit, debuggable place and lets views resolve use cases without
 * prop-drilling or a module-bound default per service.
 *
 * Layer rules it enforces by construction: only THIS file imports data/
 * adapters; views resolve through the container and never import data/
 * directly; data/ never imports the container.
 *
 * Phase 0 wired the health pipeline; Phase 2 added the content pipeline
 * (content API → repository → index/detail use cases); Phase 3 adds the
 * demo pipelines (runtime-types, runtime-async, runtime-streaming,
 * http-headers, fastapi-app-info — API → repository → use case) that live
 * demo components resolve.
 *
 * `initialize` is idempotent — re-running it just re-registers. Call it once
 * at startup (main.tsx) or in a test's beforeAll.
 */

/** Symbol tokens — the single registry of injectable service identities. */
export const ContainerTokens = {
  AppConfig: Symbol('AppConfig'),
  HealthApi: Symbol('HealthApi'),
  HealthRepository: Symbol('HealthRepository'),
  GetHealthUseCase: Symbol('GetHealthUseCase'),
  ContentApi: Symbol('ContentApi'),
  ContentRepository: Symbol('ContentRepository'),
  ListContentUseCase: Symbol('ListContentUseCase'),
  GetTopicDetailUseCase: Symbol('GetTopicDetailUseCase'),
  RuntimeTypesApi: Symbol('RuntimeTypesApi'),
  RuntimeTypesRepository: Symbol('RuntimeTypesRepository'),
  GetRuntimeTypesDemoUseCase: Symbol('GetRuntimeTypesDemoUseCase'),
  RuntimeAsyncApi: Symbol('RuntimeAsyncApi'),
  RuntimeAsyncRepository: Symbol('RuntimeAsyncRepository'),
  GetRuntimeAsyncDemoUseCase: Symbol('GetRuntimeAsyncDemoUseCase'),
  RuntimeStreamingApi: Symbol('RuntimeStreamingApi'),
  RuntimeStreamingRepository: Symbol('RuntimeStreamingRepository'),
  GetRuntimeStreamingDemoUseCase: Symbol('GetRuntimeStreamingDemoUseCase'),
  HttpHeadersApi: Symbol('HttpHeadersApi'),
  HttpHeadersRepository: Symbol('HttpHeadersRepository'),
  GetHttpHeadersDemoUseCase: Symbol('GetHttpHeadersDemoUseCase'),
  FastApiAppInfoApi: Symbol('FastApiAppInfoApi'),
  FastApiAppInfoRepository: Symbol('FastApiAppInfoRepository'),
  GetFastApiAppInfoDemoUseCase: Symbol('GetFastApiAppInfoDemoUseCase'),
  PydLabApi: Symbol('PydLabApi'),
  PydLabRepository: Symbol('PydLabRepository'),
  GetPydLabDemoUseCase: Symbol('GetPydLabDemoUseCase'),
  DepLifecycleApi: Symbol('DepLifecycleApi'),
  DepLifecycleRepository: Symbol('DepLifecycleRepository'),
  GetDepLifecycleDemoUseCase: Symbol('GetDepLifecycleDemoUseCase'),
  DepMatrixApi: Symbol('DepMatrixApi'),
  DepMatrixRepository: Symbol('DepMatrixRepository'),
  GetDepMatrixDemoUseCase: Symbol('GetDepMatrixDemoUseCase'),
  RoutingExplorerApi: Symbol('RoutingExplorerApi'),
  RoutingExplorerRepository: Symbol('RoutingExplorerRepository'),
  GetRoutingExplorerDemoUseCase: Symbol('GetRoutingExplorerDemoUseCase'),
  MiddlewarePipelineApi: Symbol('MiddlewarePipelineApi'),
  MiddlewarePipelineRepository: Symbol('MiddlewarePipelineRepository'),
  GetMiddlewarePipelineDemoUseCase: Symbol('GetMiddlewarePipelineDemoUseCase'),
  ReqresInspectorApi: Symbol('ReqresInspectorApi'),
  ReqresInspectorRepository: Symbol('ReqresInspectorRepository'),
  GetReqresInspectorDemoUseCase: Symbol('GetReqresInspectorDemoUseCase'),
  ReqresMethodsApi: Symbol('ReqresMethodsApi'),
  ReqresMethodsRepository: Symbol('ReqresMethodsRepository'),
  ReqresMethodsDemoUseCase: Symbol('ReqresMethodsDemoUseCase'),
  ValidationArenaApi: Symbol('ValidationArenaApi'),
  ValidationArenaRepository: Symbol('ValidationArenaRepository'),
  GetValidationArenaDemoUseCase: Symbol('GetValidationArenaDemoUseCase'),
  PostsWorkbenchApi: Symbol('PostsWorkbenchApi'),
  PostsWorkbenchRepository: Symbol('PostsWorkbenchRepository'),
  GetPostsWorkbenchDemoUseCase: Symbol('GetPostsWorkbenchDemoUseCase'),
  DocsLinkApi: Symbol('DocsLinkApi'),
  DocsLinkRepository: Symbol('DocsLinkRepository'),
  GetDocsLinkDemoUseCase: Symbol('GetDocsLinkDemoUseCase'),
  GraphqlPlaygroundApi: Symbol('GraphqlPlaygroundApi'),
  GraphqlPlaygroundRepository: Symbol('GraphqlPlaygroundRepository'),
  GetGraphqlPlaygroundDemoUseCase: Symbol('GetGraphqlPlaygroundDemoUseCase'),
  WebhookSimulatorApi: Symbol('WebhookSimulatorApi'),
  WebhookSimulatorRepository: Symbol('WebhookSimulatorRepository'),
  GetWebhookSimulatorDemoUseCase: Symbol('GetWebhookSimulatorDemoUseCase'),
  GrpcConsoleApi: Symbol('GrpcConsoleApi'),
  GrpcConsoleRepository: Symbol('GrpcConsoleRepository'),
  GetGrpcConsoleDemoUseCase: Symbol('GetGrpcConsoleDemoUseCase'),
  SchemaExplorerApi: Symbol('SchemaExplorerApi'),
  SchemaExplorerRepository: Symbol('SchemaExplorerRepository'),
  GetSchemaExplorerDemoUseCase: Symbol('GetSchemaExplorerDemoUseCase'),
  UuidLabApi: Symbol('UuidLabApi'),
  UuidLabRepository: Symbol('UuidLabRepository'),
  GetUuidLabDemoUseCase: Symbol('GetUuidLabDemoUseCase'),
  SqlSafetyApi: Symbol('SqlSafetyApi'),
  SqlSafetyRepository: Symbol('SqlSafetyRepository'),
  GetSqlSafetyDemoUseCase: Symbol('GetSqlSafetyDemoUseCase'),
  DbMigrationsApi: Symbol('DbMigrationsApi'),
  DbMigrationsRepository: Symbol('DbMigrationsRepository'),
  GetDbMigrationsDemoUseCase: Symbol('GetDbMigrationsDemoUseCase'),
  SqlLabApi: Symbol('SqlLabApi'),
  SqlLabRepository: Symbol('SqlLabRepository'),
  GetSqlLabDemoUseCase: Symbol('GetSqlLabDemoUseCase'),
  DbSearchApi: Symbol('DbSearchApi'),
  DbSearchRepository: Symbol('DbSearchRepository'),
  GetDbSearchDemoUseCase: Symbol('GetDbSearchDemoUseCase'),
  DbRaceApi: Symbol('DbRaceApi'),
  DbRaceRepository: Symbol('DbRaceRepository'),
  GetDbRaceDemoUseCase: Symbol('GetDbRaceDemoUseCase'),
  DbAuditApi: Symbol('DbAuditApi'),
  DbAuditRepository: Symbol('DbAuditRepository'),
  GetDbAuditDemoUseCase: Symbol('GetDbAuditDemoUseCase'),
  DbOrmProbeApi: Symbol('DbOrmProbeApi'),
  DbOrmProbeRepository: Symbol('DbOrmProbeRepository'),
  GetDbOrmProbeDemoUseCase: Symbol('GetDbOrmProbeDemoUseCase'),
  MongoConsoleApi: Symbol('MongoConsoleApi'),
  MongoConsoleRepository: Symbol('MongoConsoleRepository'),
  GetMongoConsoleDemoUseCase: Symbol('GetMongoConsoleDemoUseCase'),
  RedisPlaygroundApi: Symbol('RedisPlaygroundApi'),
  RedisPlaygroundRepository: Symbol('RedisPlaygroundRepository'),
  GetRedisPlaygroundDemoUseCase: Symbol('GetRedisPlaygroundDemoUseCase'),
  CachingLabApi: Symbol('CachingLabApi'),
  CachingLabRepository: Symbol('CachingLabRepository'),
  GetCachingLabDemoUseCase: Symbol('GetCachingLabDemoUseCase'),
  MsgStreamApi: Symbol('MsgStreamApi'),
  MsgStreamRepository: Symbol('MsgStreamRepository'),
  GetMsgStreamDemoUseCase: Symbol('GetMsgStreamDemoUseCase'),
  MsgOutboxApi: Symbol('MsgOutboxApi'),
  MsgOutboxRepository: Symbol('MsgOutboxRepository'),
  GetMsgOutboxDemoUseCase: Symbol('GetMsgOutboxDemoUseCase'),
  AuthSessionsApi: Symbol('AuthSessionsApi'),
  AuthSessionsRepository: Symbol('AuthSessionsRepository'),
  GetAuthSessionsDemoUseCase: Symbol('GetAuthSessionsDemoUseCase'),
  AuthApiKeysApi: Symbol('AuthApiKeysApi'),
  AuthApiKeysRepository: Symbol('AuthApiKeysRepository'),
  GetAuthApiKeysDemoUseCase: Symbol('GetAuthApiKeysDemoUseCase'),
  AuthJwtApi: Symbol('AuthJwtApi'),
  AuthJwtRepository: Symbol('AuthJwtRepository'),
  GetAuthJwtDemoUseCase: Symbol('GetAuthJwtDemoUseCase'),
  AuthOauthApi: Symbol('AuthOauthApi'),
  AuthOauthRepository: Symbol('AuthOauthRepository'),
  GetAuthOauthDemoUseCase: Symbol('GetAuthOauthDemoUseCase'),
  AuthHashingApi: Symbol('AuthHashingApi'),
  AuthHashingRepository: Symbol('AuthHashingRepository'),
  GetAuthHashingDemoUseCase: Symbol('GetAuthHashingDemoUseCase'),
  AuthRefreshApi: Symbol('AuthRefreshApi'),
  AuthRefreshRepository: Symbol('AuthRefreshRepository'),
  GetAuthRefreshDemoUseCase: Symbol('GetAuthRefreshDemoUseCase'),
  AuthzMatrixApi: Symbol('AuthzMatrixApi'),
  AuthzMatrixRepository: Symbol('AuthzMatrixRepository'),
  GetAuthzMatrixDemoUseCase: Symbol('GetAuthzMatrixDemoUseCase'),
  SecurityLabApi: Symbol('SecurityLabApi'),
  SecurityLabRepository: Symbol('SecurityLabRepository'),
  GetSecurityLabDemoUseCase: Symbol('GetSecurityLabDemoUseCase'),
  SecurityPiiApi: Symbol('SecurityPiiApi'),
  SecurityPiiRepository: Symbol('SecurityPiiRepository'),
  GetSecurityPiiDemoUseCase: Symbol('GetSecurityPiiDemoUseCase'),
  FilesWorkbenchApi: Symbol('FilesWorkbenchApi'),
  FilesWorkbenchRepository: Symbol('FilesWorkbenchRepository'),
  GetFilesWorkbenchDemoUseCase: Symbol('GetFilesWorkbenchDemoUseCase'),
  I18nNegotiatorApi: Symbol('I18nNegotiatorApi'),
  I18nNegotiatorRepository: Symbol('I18nNegotiatorRepository'),
  GetI18nNegotiatorDemoUseCase: Symbol('GetI18nNegotiatorDemoUseCase'),
  RealtimeTickerApi: Symbol('RealtimeTickerApi'),
  RealtimeTickerRepository: Symbol('RealtimeTickerRepository'),
  GetRealtimeTickerDemoUseCase: Symbol('GetRealtimeTickerDemoUseCase'),
  RealtimeChatApi: Symbol('RealtimeChatApi'),
  RealtimeChatRepository: Symbol('RealtimeChatRepository'),
  GetRealtimeChatDemoUseCase: Symbol('GetRealtimeChatDemoUseCase'),
  JobsConsoleApi: Symbol('JobsConsoleApi'),
  JobsConsoleRepository: Symbol('JobsConsoleRepository'),
  GetJobsConsoleDemoUseCase: Symbol('GetJobsConsoleDemoUseCase'),
  ErrorsExplorerApi: Symbol('ErrorsExplorerApi'),
  ErrorsExplorerRepository: Symbol('ErrorsExplorerRepository'),
  GetErrorsExplorerDemoUseCase: Symbol('GetErrorsExplorerDemoUseCase'),
  ArchTracerApi: Symbol('ArchTracerApi'),
  ArchTracerRepository: Symbol('ArchTracerRepository'),
  GetArchTracerDemoUseCase: Symbol('GetArchTracerDemoUseCase'),
  TestingRunnerApi: Symbol('TestingRunnerApi'),
  TestingRunnerRepository: Symbol('TestingRunnerRepository'),
  GetTestingRunnerDemoUseCase: Symbol('GetTestingRunnerDemoUseCase'),
  EnvInspectorApi: Symbol('EnvInspectorApi'),
  EnvInspectorRepository: Symbol('EnvInspectorRepository'),
  GetEnvInspectorDemoUseCase: Symbol('GetEnvInspectorDemoUseCase'),
  BestChecklistApi: Symbol('BestChecklistApi'),
  BestChecklistRepository: Symbol('BestChecklistRepository'),
  GetBestChecklistDemoUseCase: Symbol('GetBestChecklistDemoUseCase'),
} as const;

class Container {
  private readonly registry = new Map<symbol, unknown>();

  initialize(config: AppConfig): void {
    // Eager singletons — the full graph, config → api → repository → use case,
    // mirroring the server's composition-root wiring.
    this.register(ContainerTokens.AppConfig, config);

    this.register(ContainerTokens.HealthApi, new HealthApi(config));
    this.register(
      ContainerTokens.HealthRepository,
      new HealthRepositoryImpl(this.healthApi),
    );
    this.register(
      ContainerTokens.GetHealthUseCase,
      new GetHealthUseCase(this.healthRepository),
    );

    this.register(ContainerTokens.ContentApi, new ContentApi(config));
    this.register(
      ContainerTokens.ContentRepository,
      new ContentRepositoryImpl(this.contentApi),
    );
    this.register(
      ContainerTokens.ListContentUseCase,
      new ListContentUseCase(this.contentRepository),
    );
    this.register(
      ContainerTokens.GetTopicDetailUseCase,
      new GetTopicDetailUseCase(this.contentRepository),
    );

    this.register(ContainerTokens.RuntimeTypesApi, new RuntimeTypesApi(config));
    this.register(
      ContainerTokens.RuntimeTypesRepository,
      new RuntimeTypesRepositoryImpl(this.runtimeTypesApi),
    );
    this.register(
      ContainerTokens.GetRuntimeTypesDemoUseCase,
      new GetRuntimeTypesDemoUseCase(this.runtimeTypesRepository),
    );

    this.register(ContainerTokens.RuntimeAsyncApi, new RuntimeAsyncApi(config));
    this.register(
      ContainerTokens.RuntimeAsyncRepository,
      new RuntimeAsyncRepositoryImpl(this.runtimeAsyncApi),
    );
    this.register(
      ContainerTokens.GetRuntimeAsyncDemoUseCase,
      new GetRuntimeAsyncDemoUseCase(this.runtimeAsyncRepository),
    );

    this.register(ContainerTokens.RuntimeStreamingApi, new RuntimeStreamingApi(config));
    this.register(
      ContainerTokens.RuntimeStreamingRepository,
      new RuntimeStreamingRepositoryImpl(this.runtimeStreamingApi),
    );
    this.register(
      ContainerTokens.GetRuntimeStreamingDemoUseCase,
      new GetRuntimeStreamingDemoUseCase(this.runtimeStreamingRepository),
    );

    this.register(ContainerTokens.HttpHeadersApi, new HttpHeadersApi(config));
    this.register(
      ContainerTokens.HttpHeadersRepository,
      new HttpHeadersRepositoryImpl(this.httpHeadersApi),
    );
    this.register(
      ContainerTokens.GetHttpHeadersDemoUseCase,
      new GetHttpHeadersDemoUseCase(this.httpHeadersRepository),
    );

    this.register(ContainerTokens.FastApiAppInfoApi, new FastApiAppInfoApi(config));
    this.register(
      ContainerTokens.FastApiAppInfoRepository,
      new FastApiAppInfoRepositoryImpl(this.fastApiAppInfoApi),
    );
    this.register(
      ContainerTokens.GetFastApiAppInfoDemoUseCase,
      new GetFastApiAppInfoDemoUseCase(this.fastApiAppInfoRepository),
    );

    this.register(ContainerTokens.PydLabApi, new PydLabApi(config));
    this.register(
      ContainerTokens.PydLabRepository,
      new PydLabRepositoryImpl(this.pydLabApi),
    );
    this.register(
      ContainerTokens.GetPydLabDemoUseCase,
      new GetPydLabDemoUseCase(this.pydLabRepository),
    );

    this.register(ContainerTokens.DepLifecycleApi, new DepLifecycleApi(config));
    this.register(
      ContainerTokens.DepLifecycleRepository,
      new DepLifecycleRepositoryImpl(this.depLifecycleApi),
    );
    this.register(
      ContainerTokens.GetDepLifecycleDemoUseCase,
      new GetDepLifecycleDemoUseCase(this.depLifecycleRepository),
    );

    this.register(ContainerTokens.DepMatrixApi, new DepMatrixApi(config));
    this.register(
      ContainerTokens.DepMatrixRepository,
      new DepMatrixRepositoryImpl(this.depMatrixApi),
    );
    this.register(
      ContainerTokens.GetDepMatrixDemoUseCase,
      new GetDepMatrixDemoUseCase(this.depMatrixRepository),
    );

    this.register(ContainerTokens.RoutingExplorerApi, new RoutingExplorerApi(config));
    this.register(
      ContainerTokens.RoutingExplorerRepository,
      new RoutingExplorerRepositoryImpl(this.routingExplorerApi),
    );
    this.register(
      ContainerTokens.GetRoutingExplorerDemoUseCase,
      new GetRoutingExplorerDemoUseCase(this.routingExplorerRepository),
    );

    this.register(ContainerTokens.MiddlewarePipelineApi, new MiddlewarePipelineApi(config));
    this.register(
      ContainerTokens.MiddlewarePipelineRepository,
      new MiddlewarePipelineRepositoryImpl(this.middlewarePipelineApi),
    );
    this.register(
      ContainerTokens.GetMiddlewarePipelineDemoUseCase,
      new GetMiddlewarePipelineDemoUseCase(this.middlewarePipelineRepository),
    );

    this.register(ContainerTokens.ReqresInspectorApi, new ReqresInspectorApi(config));
    this.register(
      ContainerTokens.ReqresInspectorRepository,
      new ReqresInspectorRepositoryImpl(this.reqresInspectorApi),
    );
    this.register(
      ContainerTokens.GetReqresInspectorDemoUseCase,
      new GetReqresInspectorDemoUseCase(this.reqresInspectorRepository),
    );

    this.register(ContainerTokens.ReqresMethodsApi, new ReqresMethodsApi(config));
    this.register(
      ContainerTokens.ReqresMethodsRepository,
      new ReqresMethodsRepositoryImpl(this.reqresMethodsApi),
    );
    this.register(
      ContainerTokens.ReqresMethodsDemoUseCase,
      new ReqresMethodsDemoUseCase(this.reqresMethodsRepository),
    );

    this.register(ContainerTokens.ValidationArenaApi, new ValidationArenaApi(config));
    this.register(
      ContainerTokens.ValidationArenaRepository,
      new ValidationArenaRepositoryImpl(this.validationArenaApi),
    );
    this.register(
      ContainerTokens.GetValidationArenaDemoUseCase,
      new GetValidationArenaDemoUseCase(this.validationArenaRepository),
    );

    this.register(ContainerTokens.PostsWorkbenchApi, new PostsWorkbenchApi(config));
    this.register(
      ContainerTokens.PostsWorkbenchRepository,
      new PostsWorkbenchRepositoryImpl(this.postsWorkbenchApi),
    );
    this.register(
      ContainerTokens.GetPostsWorkbenchDemoUseCase,
      new GetPostsWorkbenchDemoUseCase(this.postsWorkbenchRepository),
    );

    this.register(ContainerTokens.DocsLinkApi, new DocsLinkApi(config));
    this.register(
      ContainerTokens.DocsLinkRepository,
      new DocsLinkRepositoryImpl(this.docsLinkApi),
    );
    this.register(
      ContainerTokens.GetDocsLinkDemoUseCase,
      new GetDocsLinkDemoUseCase(this.docsLinkRepository),
    );

    this.register(ContainerTokens.GraphqlPlaygroundApi, new GraphqlPlaygroundApi(config));
    this.register(
      ContainerTokens.GraphqlPlaygroundRepository,
      new GraphqlPlaygroundRepositoryImpl(this.graphqlPlaygroundApi),
    );
    this.register(
      ContainerTokens.GetGraphqlPlaygroundDemoUseCase,
      new GetGraphqlPlaygroundDemoUseCase(this.graphqlPlaygroundRepository),
    );

    this.register(ContainerTokens.WebhookSimulatorApi, new WebhookSimulatorApi(config));
    this.register(
      ContainerTokens.WebhookSimulatorRepository,
      new WebhookSimulatorRepositoryImpl(this.webhookSimulatorApi),
    );
    this.register(
      ContainerTokens.GetWebhookSimulatorDemoUseCase,
      new GetWebhookSimulatorDemoUseCase(this.webhookSimulatorRepository),
    );

    this.register(ContainerTokens.GrpcConsoleApi, new GrpcConsoleApi(config));
    this.register(
      ContainerTokens.GrpcConsoleRepository,
      new GrpcConsoleRepositoryImpl(this.grpcConsoleApi),
    );
    this.register(
      ContainerTokens.GetGrpcConsoleDemoUseCase,
      new GetGrpcConsoleDemoUseCase(this.grpcConsoleRepository),
    );

    this.register(ContainerTokens.SchemaExplorerApi, new SchemaExplorerApi(config));
    this.register(
      ContainerTokens.SchemaExplorerRepository,
      new SchemaExplorerRepositoryImpl(this.schemaExplorerApi),
    );
    this.register(
      ContainerTokens.GetSchemaExplorerDemoUseCase,
      new GetSchemaExplorerDemoUseCase(this.schemaExplorerRepository),
    );

    this.register(ContainerTokens.UuidLabApi, new UuidLabApi(config));
    this.register(
      ContainerTokens.UuidLabRepository,
      new UuidLabRepositoryImpl(this.uuidLabApi),
    );
    this.register(
      ContainerTokens.GetUuidLabDemoUseCase,
      new GetUuidLabDemoUseCase(this.uuidLabRepository),
    );

    this.register(ContainerTokens.SqlSafetyApi, new SqlSafetyApi(config));
    this.register(
      ContainerTokens.SqlSafetyRepository,
      new SqlSafetyRepositoryImpl(this.sqlSafetyApi),
    );
    this.register(
      ContainerTokens.GetSqlSafetyDemoUseCase,
      new GetSqlSafetyDemoUseCase(this.sqlSafetyRepository),
    );

    this.register(ContainerTokens.DbMigrationsApi, new DbMigrationsApi(config));
    this.register(
      ContainerTokens.DbMigrationsRepository,
      new DbMigrationsRepositoryImpl(this.dbMigrationsApi),
    );
    this.register(
      ContainerTokens.GetDbMigrationsDemoUseCase,
      new GetDbMigrationsDemoUseCase(this.dbMigrationsRepository),
    );

    this.register(ContainerTokens.SqlLabApi, new SqlLabApi(config));
    this.register(
      ContainerTokens.SqlLabRepository,
      new SqlLabRepositoryImpl(this.sqlLabApi),
    );
    this.register(
      ContainerTokens.GetSqlLabDemoUseCase,
      new GetSqlLabDemoUseCase(this.sqlLabRepository),
    );

    this.register(ContainerTokens.DbSearchApi, new DbSearchApi(config));
    this.register(
      ContainerTokens.DbSearchRepository,
      new DbSearchRepositoryImpl(this.dbSearchApi),
    );
    this.register(
      ContainerTokens.GetDbSearchDemoUseCase,
      new GetDbSearchDemoUseCase(this.dbSearchRepository),
    );

    this.register(ContainerTokens.DbRaceApi, new DbRaceApi(config));
    this.register(
      ContainerTokens.DbRaceRepository,
      new DbRaceRepositoryImpl(this.dbRaceApi),
    );
    this.register(
      ContainerTokens.GetDbRaceDemoUseCase,
      new GetDbRaceDemoUseCase(this.dbRaceRepository),
    );

    this.register(ContainerTokens.DbAuditApi, new DbAuditApi(config));
    this.register(
      ContainerTokens.DbAuditRepository,
      new DbAuditRepositoryImpl(this.dbAuditApi),
    );
    this.register(
      ContainerTokens.GetDbAuditDemoUseCase,
      new GetDbAuditDemoUseCase(this.dbAuditRepository),
    );

    this.register(ContainerTokens.DbOrmProbeApi, new DbOrmProbeApi(config));
    this.register(
      ContainerTokens.DbOrmProbeRepository,
      new DbOrmProbeRepositoryImpl(this.dbOrmProbeApi),
    );
    this.register(
      ContainerTokens.GetDbOrmProbeDemoUseCase,
      new GetDbOrmProbeDemoUseCase(this.dbOrmProbeRepository),
    );

    this.register(ContainerTokens.MongoConsoleApi, new MongoConsoleApi(config));
    this.register(
      ContainerTokens.MongoConsoleRepository,
      new MongoConsoleRepositoryImpl(this.mongoConsoleApi),
    );
    this.register(
      ContainerTokens.GetMongoConsoleDemoUseCase,
      new GetMongoConsoleDemoUseCase(this.mongoConsoleRepository),
    );

    this.register(ContainerTokens.RedisPlaygroundApi, new RedisPlaygroundApi(config));
    this.register(
      ContainerTokens.RedisPlaygroundRepository,
      new RedisPlaygroundRepositoryImpl(this.redisPlaygroundApi),
    );
    this.register(
      ContainerTokens.GetRedisPlaygroundDemoUseCase,
      new GetRedisPlaygroundDemoUseCase(this.redisPlaygroundRepository),
    );

    this.register(ContainerTokens.CachingLabApi, new CachingLabApi(config));
    this.register(
      ContainerTokens.CachingLabRepository,
      new CachingLabRepositoryImpl(this.cachingLabApi),
    );
    this.register(
      ContainerTokens.GetCachingLabDemoUseCase,
      new GetCachingLabDemoUseCase(this.cachingLabRepository),
    );

    this.register(ContainerTokens.MsgStreamApi, new MsgStreamApi(config));
    this.register(
      ContainerTokens.MsgStreamRepository,
      new MsgStreamRepositoryImpl(this.msgStreamApi),
    );
    this.register(
      ContainerTokens.GetMsgStreamDemoUseCase,
      new GetMsgStreamDemoUseCase(this.msgStreamRepository),
    );

    this.register(ContainerTokens.MsgOutboxApi, new MsgOutboxApi(config));
    this.register(
      ContainerTokens.MsgOutboxRepository,
      new MsgOutboxRepositoryImpl(this.msgOutboxApi),
    );
    this.register(
      ContainerTokens.GetMsgOutboxDemoUseCase,
      new GetMsgOutboxDemoUseCase(this.msgOutboxRepository),
    );

    this.register(ContainerTokens.AuthSessionsApi, new AuthSessionsApi(config));
    this.register(
      ContainerTokens.AuthSessionsRepository,
      new AuthSessionsRepositoryImpl(this.authSessionsApi),
    );
    this.register(
      ContainerTokens.GetAuthSessionsDemoUseCase,
      new GetAuthSessionsDemoUseCase(this.authSessionsRepository),
    );

    this.register(ContainerTokens.AuthApiKeysApi, new AuthApiKeysApi(config));
    this.register(
      ContainerTokens.AuthApiKeysRepository,
      new AuthApiKeysRepositoryImpl(this.authApiKeysApi),
    );
    this.register(
      ContainerTokens.GetAuthApiKeysDemoUseCase,
      new GetAuthApiKeysDemoUseCase(this.authApiKeysRepository),
    );

    this.register(ContainerTokens.AuthJwtApi, new AuthJwtApi(config));
    this.register(
      ContainerTokens.AuthJwtRepository,
      new AuthJwtRepositoryImpl(this.authJwtApi),
    );
    this.register(
      ContainerTokens.GetAuthJwtDemoUseCase,
      new GetAuthJwtDemoUseCase(this.authJwtRepository),
    );

    this.register(ContainerTokens.AuthOauthApi, new AuthOauthApi(config));
    this.register(
      ContainerTokens.AuthOauthRepository,
      new AuthOauthRepositoryImpl(this.authOauthApi),
    );
    this.register(
      ContainerTokens.GetAuthOauthDemoUseCase,
      new GetAuthOauthDemoUseCase(this.authOauthRepository),
    );

    this.register(ContainerTokens.AuthHashingApi, new AuthHashingApi(config));
    this.register(
      ContainerTokens.AuthHashingRepository,
      new AuthHashingRepositoryImpl(this.authHashingApi),
    );
    this.register(
      ContainerTokens.GetAuthHashingDemoUseCase,
      new GetAuthHashingDemoUseCase(this.authHashingRepository),
    );

    this.register(ContainerTokens.AuthRefreshApi, new AuthRefreshApi(config));
    this.register(
      ContainerTokens.AuthRefreshRepository,
      new AuthRefreshRepositoryImpl(this.authRefreshApi),
    );
    this.register(
      ContainerTokens.GetAuthRefreshDemoUseCase,
      new GetAuthRefreshDemoUseCase(this.authRefreshRepository),
    );

    this.register(ContainerTokens.AuthzMatrixApi, new AuthzMatrixApi(config));
    this.register(
      ContainerTokens.AuthzMatrixRepository,
      new AuthzMatrixRepositoryImpl(this.authzMatrixApi),
    );
    this.register(
      ContainerTokens.GetAuthzMatrixDemoUseCase,
      new GetAuthzMatrixDemoUseCase(this.authzMatrixRepository),
    );

    this.register(ContainerTokens.SecurityLabApi, new SecurityLabApi(config));
    this.register(
      ContainerTokens.SecurityLabRepository,
      new SecurityLabRepositoryImpl(this.securityLabApi),
    );
    this.register(
      ContainerTokens.GetSecurityLabDemoUseCase,
      new GetSecurityLabDemoUseCase(this.securityLabRepository),
    );

    this.register(ContainerTokens.SecurityPiiApi, new SecurityPiiApi(config));
    this.register(
      ContainerTokens.SecurityPiiRepository,
      new SecurityPiiRepositoryImpl(this.securityPiiApi),
    );
    this.register(
      ContainerTokens.GetSecurityPiiDemoUseCase,
      new GetSecurityPiiDemoUseCase(this.securityPiiRepository),
    );

    this.register(ContainerTokens.FilesWorkbenchApi, new FilesWorkbenchApi(config));
    this.register(
      ContainerTokens.FilesWorkbenchRepository,
      new FilesWorkbenchRepositoryImpl(this.filesWorkbenchApi),
    );
    this.register(
      ContainerTokens.GetFilesWorkbenchDemoUseCase,
      new GetFilesWorkbenchDemoUseCase(this.filesWorkbenchRepository),
    );

    this.register(ContainerTokens.I18nNegotiatorApi, new I18nNegotiatorApi(config));
    this.register(
      ContainerTokens.I18nNegotiatorRepository,
      new I18nNegotiatorRepositoryImpl(this.i18nNegotiatorApi),
    );
    this.register(
      ContainerTokens.GetI18nNegotiatorDemoUseCase,
      new GetI18nNegotiatorDemoUseCase(this.i18nNegotiatorRepository),
    );

    this.register(ContainerTokens.RealtimeTickerApi, new RealtimeTickerApi(config));
    this.register(
      ContainerTokens.RealtimeTickerRepository,
      new RealtimeTickerRepositoryImpl(this.realtimeTickerApi),
    );
    this.register(
      ContainerTokens.GetRealtimeTickerDemoUseCase,
      new GetRealtimeTickerDemoUseCase(this.realtimeTickerRepository),
    );

    this.register(ContainerTokens.RealtimeChatApi, new RealtimeChatApi(config));
    this.register(
      ContainerTokens.RealtimeChatRepository,
      new RealtimeChatRepositoryImpl(this.realtimeChatApi),
    );
    this.register(
      ContainerTokens.GetRealtimeChatDemoUseCase,
      new GetRealtimeChatDemoUseCase(this.realtimeChatRepository),
    );

    this.register(ContainerTokens.JobsConsoleApi, new JobsConsoleApi(config));
    this.register(
      ContainerTokens.JobsConsoleRepository,
      new JobsConsoleRepositoryImpl(this.jobsConsoleApi),
    );
    this.register(
      ContainerTokens.GetJobsConsoleDemoUseCase,
      new GetJobsConsoleDemoUseCase(this.jobsConsoleRepository),
    );

    this.register(ContainerTokens.ErrorsExplorerApi, new ErrorsExplorerApi(config));
    this.register(
      ContainerTokens.ErrorsExplorerRepository,
      new ErrorsExplorerRepositoryImpl(this.errorsExplorerApi),
    );
    this.register(
      ContainerTokens.GetErrorsExplorerDemoUseCase,
      new GetErrorsExplorerDemoUseCase(this.errorsExplorerRepository),
    );

    this.register(ContainerTokens.ArchTracerApi, new ArchTracerApi(config));
    this.register(
      ContainerTokens.ArchTracerRepository,
      new ArchTracerRepositoryImpl(this.archTracerApi),
    );
    this.register(
      ContainerTokens.GetArchTracerDemoUseCase,
      new GetArchTracerDemoUseCase(this.archTracerRepository),
    );

    this.register(ContainerTokens.TestingRunnerApi, new TestingRunnerApi(config));
    this.register(
      ContainerTokens.TestingRunnerRepository,
      new TestingRunnerRepositoryImpl(this.testingRunnerApi),
    );
    this.register(
      ContainerTokens.GetTestingRunnerDemoUseCase,
      new GetTestingRunnerDemoUseCase(this.testingRunnerRepository),
    );

    this.register(ContainerTokens.EnvInspectorApi, new EnvInspectorApi(config));
    this.register(
      ContainerTokens.EnvInspectorRepository,
      new EnvInspectorRepositoryImpl(this.envInspectorApi),
    );
    this.register(
      ContainerTokens.GetEnvInspectorDemoUseCase,
      new GetEnvInspectorDemoUseCase(this.envInspectorRepository),
    );

    this.register(ContainerTokens.BestChecklistApi, new BestChecklistApi(config));
    this.register(
      ContainerTokens.BestChecklistRepository,
      new BestChecklistRepositoryImpl(this.bestChecklistApi),
    );
    this.register(
      ContainerTokens.GetBestChecklistDemoUseCase,
      new GetBestChecklistDemoUseCase(this.bestChecklistRepository),
    );
  }

  // ---- typed service accessors (the only names views should use) ----

  get appConfig(): AppConfig {
    return this.resolve<AppConfig>(ContainerTokens.AppConfig);
  }
  get healthApi(): HealthApi {
    return this.resolve<HealthApi>(ContainerTokens.HealthApi);
  }
  get healthRepository(): HealthRepository {
    return this.resolve<HealthRepository>(ContainerTokens.HealthRepository);
  }
  get getHealthUseCase(): GetHealthUseCase {
    return this.resolve<GetHealthUseCase>(ContainerTokens.GetHealthUseCase);
  }
  get contentApi(): ContentApi {
    return this.resolve<ContentApi>(ContainerTokens.ContentApi);
  }
  get contentRepository(): ContentRepository {
    return this.resolve<ContentRepository>(ContainerTokens.ContentRepository);
  }
  get listContentUseCase(): ListContentUseCase {
    return this.resolve<ListContentUseCase>(ContainerTokens.ListContentUseCase);
  }
  get getTopicDetailUseCase(): GetTopicDetailUseCase {
    return this.resolve<GetTopicDetailUseCase>(ContainerTokens.GetTopicDetailUseCase);
  }
  get runtimeTypesApi(): RuntimeTypesApi {
    return this.resolve<RuntimeTypesApi>(ContainerTokens.RuntimeTypesApi);
  }
  get runtimeTypesRepository(): RuntimeTypesRepository {
    return this.resolve<RuntimeTypesRepository>(ContainerTokens.RuntimeTypesRepository);
  }
  get getRuntimeTypesDemoUseCase(): GetRuntimeTypesDemoUseCase {
    return this.resolve<GetRuntimeTypesDemoUseCase>(ContainerTokens.GetRuntimeTypesDemoUseCase);
  }
  get runtimeAsyncApi(): RuntimeAsyncApi {
    return this.resolve<RuntimeAsyncApi>(ContainerTokens.RuntimeAsyncApi);
  }
  get runtimeAsyncRepository(): RuntimeAsyncRepository {
    return this.resolve<RuntimeAsyncRepository>(ContainerTokens.RuntimeAsyncRepository);
  }
  get getRuntimeAsyncDemoUseCase(): GetRuntimeAsyncDemoUseCase {
    return this.resolve<GetRuntimeAsyncDemoUseCase>(ContainerTokens.GetRuntimeAsyncDemoUseCase);
  }
  get runtimeStreamingApi(): RuntimeStreamingApi {
    return this.resolve<RuntimeStreamingApi>(ContainerTokens.RuntimeStreamingApi);
  }
  get runtimeStreamingRepository(): RuntimeStreamingRepository {
    return this.resolve<RuntimeStreamingRepository>(ContainerTokens.RuntimeStreamingRepository);
  }
  get getRuntimeStreamingDemoUseCase(): GetRuntimeStreamingDemoUseCase {
    return this.resolve<GetRuntimeStreamingDemoUseCase>(
      ContainerTokens.GetRuntimeStreamingDemoUseCase,
    );
  }
  get httpHeadersApi(): HttpHeadersApi {
    return this.resolve<HttpHeadersApi>(ContainerTokens.HttpHeadersApi);
  }
  get httpHeadersRepository(): HttpHeadersRepository {
    return this.resolve<HttpHeadersRepository>(ContainerTokens.HttpHeadersRepository);
  }
  get getHttpHeadersDemoUseCase(): GetHttpHeadersDemoUseCase {
    return this.resolve<GetHttpHeadersDemoUseCase>(ContainerTokens.GetHttpHeadersDemoUseCase);
  }
  get fastApiAppInfoApi(): FastApiAppInfoApi {
    return this.resolve<FastApiAppInfoApi>(ContainerTokens.FastApiAppInfoApi);
  }
  get fastApiAppInfoRepository(): FastApiAppInfoRepository {
    return this.resolve<FastApiAppInfoRepository>(ContainerTokens.FastApiAppInfoRepository);
  }
  get getFastApiAppInfoDemoUseCase(): GetFastApiAppInfoDemoUseCase {
    return this.resolve<GetFastApiAppInfoDemoUseCase>(ContainerTokens.GetFastApiAppInfoDemoUseCase);
  }
  get pydLabApi(): PydLabApi {
    return this.resolve<PydLabApi>(ContainerTokens.PydLabApi);
  }
  get pydLabRepository(): PydLabRepository {
    return this.resolve<PydLabRepository>(ContainerTokens.PydLabRepository);
  }
  get getPydLabDemoUseCase(): GetPydLabDemoUseCase {
    return this.resolve<GetPydLabDemoUseCase>(ContainerTokens.GetPydLabDemoUseCase);
  }
  get depLifecycleApi(): DepLifecycleApi {
    return this.resolve<DepLifecycleApi>(ContainerTokens.DepLifecycleApi);
  }
  get depLifecycleRepository(): DepLifecycleRepository {
    return this.resolve<DepLifecycleRepository>(ContainerTokens.DepLifecycleRepository);
  }
  get getDepLifecycleDemoUseCase(): GetDepLifecycleDemoUseCase {
    return this.resolve<GetDepLifecycleDemoUseCase>(
      ContainerTokens.GetDepLifecycleDemoUseCase,
    );
  }
  get depMatrixApi(): DepMatrixApi {
    return this.resolve<DepMatrixApi>(ContainerTokens.DepMatrixApi);
  }
  get depMatrixRepository(): DepMatrixRepository {
    return this.resolve<DepMatrixRepository>(ContainerTokens.DepMatrixRepository);
  }
  get getDepMatrixDemoUseCase(): GetDepMatrixDemoUseCase {
    return this.resolve<GetDepMatrixDemoUseCase>(ContainerTokens.GetDepMatrixDemoUseCase);
  }
  get routingExplorerApi(): RoutingExplorerApi {
    return this.resolve<RoutingExplorerApi>(ContainerTokens.RoutingExplorerApi);
  }
  get routingExplorerRepository(): RoutingExplorerRepository {
    return this.resolve<RoutingExplorerRepository>(ContainerTokens.RoutingExplorerRepository);
  }
  get getRoutingExplorerDemoUseCase(): GetRoutingExplorerDemoUseCase {
    return this.resolve<GetRoutingExplorerDemoUseCase>(
      ContainerTokens.GetRoutingExplorerDemoUseCase,
    );
  }
  get middlewarePipelineApi(): MiddlewarePipelineApi {
    return this.resolve<MiddlewarePipelineApi>(ContainerTokens.MiddlewarePipelineApi);
  }
  get middlewarePipelineRepository(): MiddlewarePipelineRepository {
    return this.resolve<MiddlewarePipelineRepository>(ContainerTokens.MiddlewarePipelineRepository);
  }
  get getMiddlewarePipelineDemoUseCase(): GetMiddlewarePipelineDemoUseCase {
    return this.resolve<GetMiddlewarePipelineDemoUseCase>(
      ContainerTokens.GetMiddlewarePipelineDemoUseCase,
    );
  }
  get reqresInspectorApi(): ReqresInspectorApi {
    return this.resolve<ReqresInspectorApi>(ContainerTokens.ReqresInspectorApi);
  }
  get reqresInspectorRepository(): ReqresInspectorRepository {
    return this.resolve<ReqresInspectorRepository>(ContainerTokens.ReqresInspectorRepository);
  }
  get getReqresInspectorDemoUseCase(): GetReqresInspectorDemoUseCase {
    return this.resolve<GetReqresInspectorDemoUseCase>(
      ContainerTokens.GetReqresInspectorDemoUseCase,
    );
  }
  get reqresMethodsApi(): ReqresMethodsApi {
    return this.resolve<ReqresMethodsApi>(ContainerTokens.ReqresMethodsApi);
  }
  get reqresMethodsRepository(): ReqresMethodsRepository {
    return this.resolve<ReqresMethodsRepository>(ContainerTokens.ReqresMethodsRepository);
  }
  get reqresMethodsDemoUseCase(): ReqresMethodsDemoUseCase {
    return this.resolve<ReqresMethodsDemoUseCase>(ContainerTokens.ReqresMethodsDemoUseCase);
  }
  get validationArenaApi(): ValidationArenaApi {
    return this.resolve<ValidationArenaApi>(ContainerTokens.ValidationArenaApi);
  }
  get validationArenaRepository(): ValidationArenaRepository {
    return this.resolve<ValidationArenaRepository>(ContainerTokens.ValidationArenaRepository);
  }
  get getValidationArenaDemoUseCase(): GetValidationArenaDemoUseCase {
    return this.resolve<GetValidationArenaDemoUseCase>(
      ContainerTokens.GetValidationArenaDemoUseCase,
    );
  }
  get postsWorkbenchApi(): PostsWorkbenchApi {
    return this.resolve<PostsWorkbenchApi>(ContainerTokens.PostsWorkbenchApi);
  }
  get postsWorkbenchRepository(): PostsWorkbenchRepository {
    return this.resolve<PostsWorkbenchRepository>(ContainerTokens.PostsWorkbenchRepository);
  }
  get getPostsWorkbenchDemoUseCase(): GetPostsWorkbenchDemoUseCase {
    return this.resolve<GetPostsWorkbenchDemoUseCase>(
      ContainerTokens.GetPostsWorkbenchDemoUseCase,
    );
  }
  get docsLinkApi(): DocsLinkApi {
    return this.resolve<DocsLinkApi>(ContainerTokens.DocsLinkApi);
  }
  get docsLinkRepository(): DocsLinkRepository {
    return this.resolve<DocsLinkRepository>(ContainerTokens.DocsLinkRepository);
  }
  get getDocsLinkDemoUseCase(): GetDocsLinkDemoUseCase {
    return this.resolve<GetDocsLinkDemoUseCase>(ContainerTokens.GetDocsLinkDemoUseCase);
  }
  get graphqlPlaygroundApi(): GraphqlPlaygroundApi {
    return this.resolve<GraphqlPlaygroundApi>(ContainerTokens.GraphqlPlaygroundApi);
  }
  get graphqlPlaygroundRepository(): GraphqlPlaygroundRepository {
    return this.resolve<GraphqlPlaygroundRepository>(ContainerTokens.GraphqlPlaygroundRepository);
  }
  get getGraphqlPlaygroundDemoUseCase(): GetGraphqlPlaygroundDemoUseCase {
    return this.resolve<GetGraphqlPlaygroundDemoUseCase>(
      ContainerTokens.GetGraphqlPlaygroundDemoUseCase,
    );
  }
  get webhookSimulatorApi(): WebhookSimulatorApi {
    return this.resolve<WebhookSimulatorApi>(ContainerTokens.WebhookSimulatorApi);
  }
  get webhookSimulatorRepository(): WebhookSimulatorRepository {
    return this.resolve<WebhookSimulatorRepository>(ContainerTokens.WebhookSimulatorRepository);
  }
  get getWebhookSimulatorDemoUseCase(): GetWebhookSimulatorDemoUseCase {
    return this.resolve<GetWebhookSimulatorDemoUseCase>(
      ContainerTokens.GetWebhookSimulatorDemoUseCase,
    );
  }
  get grpcConsoleApi(): GrpcConsoleApi {
    return this.resolve<GrpcConsoleApi>(ContainerTokens.GrpcConsoleApi);
  }
  get grpcConsoleRepository(): GrpcConsoleRepository {
    return this.resolve<GrpcConsoleRepository>(ContainerTokens.GrpcConsoleRepository);
  }
  get getGrpcConsoleDemoUseCase(): GetGrpcConsoleDemoUseCase {
    return this.resolve<GetGrpcConsoleDemoUseCase>(
      ContainerTokens.GetGrpcConsoleDemoUseCase,
    );
  }
  get schemaExplorerApi(): SchemaExplorerApi {
    return this.resolve<SchemaExplorerApi>(ContainerTokens.SchemaExplorerApi);
  }
  get schemaExplorerRepository(): SchemaExplorerRepository {
    return this.resolve<SchemaExplorerRepository>(ContainerTokens.SchemaExplorerRepository);
  }
  get getSchemaExplorerDemoUseCase(): GetSchemaExplorerDemoUseCase {
    return this.resolve<GetSchemaExplorerDemoUseCase>(
      ContainerTokens.GetSchemaExplorerDemoUseCase,
    );
  }
  get uuidLabApi(): UuidLabApi {
    return this.resolve<UuidLabApi>(ContainerTokens.UuidLabApi);
  }
  get uuidLabRepository(): UuidLabRepository {
    return this.resolve<UuidLabRepository>(ContainerTokens.UuidLabRepository);
  }
  get getUuidLabDemoUseCase(): GetUuidLabDemoUseCase {
    return this.resolve<GetUuidLabDemoUseCase>(ContainerTokens.GetUuidLabDemoUseCase);
  }
  get sqlSafetyApi(): SqlSafetyApi {
    return this.resolve<SqlSafetyApi>(ContainerTokens.SqlSafetyApi);
  }
  get sqlSafetyRepository(): SqlSafetyRepository {
    return this.resolve<SqlSafetyRepository>(ContainerTokens.SqlSafetyRepository);
  }
  get getSqlSafetyDemoUseCase(): GetSqlSafetyDemoUseCase {
    return this.resolve<GetSqlSafetyDemoUseCase>(ContainerTokens.GetSqlSafetyDemoUseCase);
  }
  get dbMigrationsApi(): DbMigrationsApi {
    return this.resolve<DbMigrationsApi>(ContainerTokens.DbMigrationsApi);
  }
  get dbMigrationsRepository(): DbMigrationsRepository {
    return this.resolve<DbMigrationsRepository>(ContainerTokens.DbMigrationsRepository);
  }
  get getDbMigrationsDemoUseCase(): GetDbMigrationsDemoUseCase {
    return this.resolve<GetDbMigrationsDemoUseCase>(
      ContainerTokens.GetDbMigrationsDemoUseCase,
    );
  }
  get sqlLabApi(): SqlLabApi {
    return this.resolve<SqlLabApi>(ContainerTokens.SqlLabApi);
  }
  get sqlLabRepository(): SqlLabRepository {
    return this.resolve<SqlLabRepository>(ContainerTokens.SqlLabRepository);
  }
  get getSqlLabDemoUseCase(): GetSqlLabDemoUseCase {
    return this.resolve<GetSqlLabDemoUseCase>(ContainerTokens.GetSqlLabDemoUseCase);
  }
  get dbSearchApi(): DbSearchApi {
    return this.resolve<DbSearchApi>(ContainerTokens.DbSearchApi);
  }
  get dbSearchRepository(): DbSearchRepository {
    return this.resolve<DbSearchRepository>(ContainerTokens.DbSearchRepository);
  }
  get getDbSearchDemoUseCase(): GetDbSearchDemoUseCase {
    return this.resolve<GetDbSearchDemoUseCase>(ContainerTokens.GetDbSearchDemoUseCase);
  }
  get dbRaceApi(): DbRaceApi {
    return this.resolve<DbRaceApi>(ContainerTokens.DbRaceApi);
  }
  get dbRaceRepository(): DbRaceRepository {
    return this.resolve<DbRaceRepository>(ContainerTokens.DbRaceRepository);
  }
  get getDbRaceDemoUseCase(): GetDbRaceDemoUseCase {
    return this.resolve<GetDbRaceDemoUseCase>(ContainerTokens.GetDbRaceDemoUseCase);
  }
  get dbAuditApi(): DbAuditApi {
    return this.resolve<DbAuditApi>(ContainerTokens.DbAuditApi);
  }
  get dbAuditRepository(): DbAuditRepository {
    return this.resolve<DbAuditRepository>(ContainerTokens.DbAuditRepository);
  }
  get getDbAuditDemoUseCase(): GetDbAuditDemoUseCase {
    return this.resolve<GetDbAuditDemoUseCase>(ContainerTokens.GetDbAuditDemoUseCase);
  }
  get dbOrmProbeApi(): DbOrmProbeApi {
    return this.resolve<DbOrmProbeApi>(ContainerTokens.DbOrmProbeApi);
  }
  get dbOrmProbeRepository(): DbOrmProbeRepository {
    return this.resolve<DbOrmProbeRepository>(ContainerTokens.DbOrmProbeRepository);
  }
  get getDbOrmProbeDemoUseCase(): GetDbOrmProbeDemoUseCase {
    return this.resolve<GetDbOrmProbeDemoUseCase>(
      ContainerTokens.GetDbOrmProbeDemoUseCase,
    );
  }
  get mongoConsoleApi(): MongoConsoleApi {
    return this.resolve<MongoConsoleApi>(ContainerTokens.MongoConsoleApi);
  }
  get mongoConsoleRepository(): MongoConsoleRepository {
    return this.resolve<MongoConsoleRepository>(ContainerTokens.MongoConsoleRepository);
  }
  get getMongoConsoleDemoUseCase(): GetMongoConsoleDemoUseCase {
    return this.resolve<GetMongoConsoleDemoUseCase>(
      ContainerTokens.GetMongoConsoleDemoUseCase,
    );
  }
  get redisPlaygroundApi(): RedisPlaygroundApi {
    return this.resolve<RedisPlaygroundApi>(ContainerTokens.RedisPlaygroundApi);
  }
  get redisPlaygroundRepository(): RedisPlaygroundRepository {
    return this.resolve<RedisPlaygroundRepository>(ContainerTokens.RedisPlaygroundRepository);
  }
  get getRedisPlaygroundDemoUseCase(): GetRedisPlaygroundDemoUseCase {
    return this.resolve<GetRedisPlaygroundDemoUseCase>(
      ContainerTokens.GetRedisPlaygroundDemoUseCase,
    );
  }
  get cachingLabApi(): CachingLabApi {
    return this.resolve<CachingLabApi>(ContainerTokens.CachingLabApi);
  }
  get cachingLabRepository(): CachingLabRepository {
    return this.resolve<CachingLabRepository>(ContainerTokens.CachingLabRepository);
  }
  get getCachingLabDemoUseCase(): GetCachingLabDemoUseCase {
    return this.resolve<GetCachingLabDemoUseCase>(ContainerTokens.GetCachingLabDemoUseCase);
  }
  get msgStreamApi(): MsgStreamApi {
    return this.resolve<MsgStreamApi>(ContainerTokens.MsgStreamApi);
  }
  get msgStreamRepository(): MsgStreamRepository {
    return this.resolve<MsgStreamRepository>(ContainerTokens.MsgStreamRepository);
  }
  get getMsgStreamDemoUseCase(): GetMsgStreamDemoUseCase {
    return this.resolve<GetMsgStreamDemoUseCase>(ContainerTokens.GetMsgStreamDemoUseCase);
  }
  get msgOutboxApi(): MsgOutboxApi {
    return this.resolve<MsgOutboxApi>(ContainerTokens.MsgOutboxApi);
  }
  get msgOutboxRepository(): MsgOutboxRepository {
    return this.resolve<MsgOutboxRepository>(ContainerTokens.MsgOutboxRepository);
  }
  get getMsgOutboxDemoUseCase(): GetMsgOutboxDemoUseCase {
    return this.resolve<GetMsgOutboxDemoUseCase>(ContainerTokens.GetMsgOutboxDemoUseCase);
  }
  get authSessionsApi(): AuthSessionsApi {
    return this.resolve<AuthSessionsApi>(ContainerTokens.AuthSessionsApi);
  }
  get authSessionsRepository(): AuthSessionsRepository {
    return this.resolve<AuthSessionsRepository>(ContainerTokens.AuthSessionsRepository);
  }
  get getAuthSessionsDemoUseCase(): GetAuthSessionsDemoUseCase {
    return this.resolve<GetAuthSessionsDemoUseCase>(ContainerTokens.GetAuthSessionsDemoUseCase);
  }
  get authApiKeysApi(): AuthApiKeysApi {
    return this.resolve<AuthApiKeysApi>(ContainerTokens.AuthApiKeysApi);
  }
  get authApiKeysRepository(): AuthApiKeysRepository {
    return this.resolve<AuthApiKeysRepository>(ContainerTokens.AuthApiKeysRepository);
  }
  get getAuthApiKeysDemoUseCase(): GetAuthApiKeysDemoUseCase {
    return this.resolve<GetAuthApiKeysDemoUseCase>(ContainerTokens.GetAuthApiKeysDemoUseCase);
  }
  get authJwtApi(): AuthJwtApi {
    return this.resolve<AuthJwtApi>(ContainerTokens.AuthJwtApi);
  }
  get authJwtRepository(): AuthJwtRepository {
    return this.resolve<AuthJwtRepository>(ContainerTokens.AuthJwtRepository);
  }
  get getAuthJwtDemoUseCase(): GetAuthJwtDemoUseCase {
    return this.resolve<GetAuthJwtDemoUseCase>(ContainerTokens.GetAuthJwtDemoUseCase);
  }
  get authOauthApi(): AuthOauthApi {
    return this.resolve<AuthOauthApi>(ContainerTokens.AuthOauthApi);
  }
  get authOauthRepository(): AuthOauthRepository {
    return this.resolve<AuthOauthRepository>(ContainerTokens.AuthOauthRepository);
  }
  get getAuthOauthDemoUseCase(): GetAuthOauthDemoUseCase {
    return this.resolve<GetAuthOauthDemoUseCase>(ContainerTokens.GetAuthOauthDemoUseCase);
  }
  get authHashingApi(): AuthHashingApi {
    return this.resolve<AuthHashingApi>(ContainerTokens.AuthHashingApi);
  }
  get authHashingRepository(): AuthHashingRepository {
    return this.resolve<AuthHashingRepository>(ContainerTokens.AuthHashingRepository);
  }
  get getAuthHashingDemoUseCase(): GetAuthHashingDemoUseCase {
    return this.resolve<GetAuthHashingDemoUseCase>(ContainerTokens.GetAuthHashingDemoUseCase);
  }
  get authRefreshApi(): AuthRefreshApi {
    return this.resolve<AuthRefreshApi>(ContainerTokens.AuthRefreshApi);
  }
  get authRefreshRepository(): AuthRefreshRepository {
    return this.resolve<AuthRefreshRepository>(ContainerTokens.AuthRefreshRepository);
  }
  get getAuthRefreshDemoUseCase(): GetAuthRefreshDemoUseCase {
    return this.resolve<GetAuthRefreshDemoUseCase>(ContainerTokens.GetAuthRefreshDemoUseCase);
  }
  get authzMatrixApi(): AuthzMatrixApi {
    return this.resolve<AuthzMatrixApi>(ContainerTokens.AuthzMatrixApi);
  }
  get authzMatrixRepository(): AuthzMatrixRepository {
    return this.resolve<AuthzMatrixRepository>(ContainerTokens.AuthzMatrixRepository);
  }
  get getAuthzMatrixDemoUseCase(): GetAuthzMatrixDemoUseCase {
    return this.resolve<GetAuthzMatrixDemoUseCase>(ContainerTokens.GetAuthzMatrixDemoUseCase);
  }
  get securityLabApi(): SecurityLabApi {
    return this.resolve<SecurityLabApi>(ContainerTokens.SecurityLabApi);
  }
  get securityLabRepository(): SecurityLabRepository {
    return this.resolve<SecurityLabRepository>(ContainerTokens.SecurityLabRepository);
  }
  get getSecurityLabDemoUseCase(): GetSecurityLabDemoUseCase {
    return this.resolve<GetSecurityLabDemoUseCase>(ContainerTokens.GetSecurityLabDemoUseCase);
  }
  get securityPiiApi(): SecurityPiiApi {
    return this.resolve<SecurityPiiApi>(ContainerTokens.SecurityPiiApi);
  }
  get securityPiiRepository(): SecurityPiiRepository {
    return this.resolve<SecurityPiiRepository>(ContainerTokens.SecurityPiiRepository);
  }
  get getSecurityPiiDemoUseCase(): GetSecurityPiiDemoUseCase {
    return this.resolve<GetSecurityPiiDemoUseCase>(ContainerTokens.GetSecurityPiiDemoUseCase);
  }
  get filesWorkbenchApi(): FilesWorkbenchApi {
    return this.resolve<FilesWorkbenchApi>(ContainerTokens.FilesWorkbenchApi);
  }
  get filesWorkbenchRepository(): FilesWorkbenchRepository {
    return this.resolve<FilesWorkbenchRepository>(ContainerTokens.FilesWorkbenchRepository);
  }
  get getFilesWorkbenchDemoUseCase(): GetFilesWorkbenchDemoUseCase {
    return this.resolve<GetFilesWorkbenchDemoUseCase>(ContainerTokens.GetFilesWorkbenchDemoUseCase);
  }
  get i18nNegotiatorApi(): I18nNegotiatorApi {
    return this.resolve<I18nNegotiatorApi>(ContainerTokens.I18nNegotiatorApi);
  }
  get i18nNegotiatorRepository(): I18nNegotiatorRepository {
    return this.resolve<I18nNegotiatorRepository>(ContainerTokens.I18nNegotiatorRepository);
  }
  get getI18nNegotiatorDemoUseCase(): GetI18nNegotiatorDemoUseCase {
    return this.resolve<GetI18nNegotiatorDemoUseCase>(
      ContainerTokens.GetI18nNegotiatorDemoUseCase,
    );
  }
  get realtimeTickerApi(): RealtimeTickerApi {
    return this.resolve<RealtimeTickerApi>(ContainerTokens.RealtimeTickerApi);
  }
  get realtimeTickerRepository(): RealtimeTickerRepository {
    return this.resolve<RealtimeTickerRepository>(ContainerTokens.RealtimeTickerRepository);
  }
  get getRealtimeTickerDemoUseCase(): GetRealtimeTickerDemoUseCase {
    return this.resolve<GetRealtimeTickerDemoUseCase>(
      ContainerTokens.GetRealtimeTickerDemoUseCase,
    );
  }
  get realtimeChatApi(): RealtimeChatApi {
    return this.resolve<RealtimeChatApi>(ContainerTokens.RealtimeChatApi);
  }
  get realtimeChatRepository(): RealtimeChatRepository {
    return this.resolve<RealtimeChatRepository>(ContainerTokens.RealtimeChatRepository);
  }
  get getRealtimeChatDemoUseCase(): GetRealtimeChatDemoUseCase {
    return this.resolve<GetRealtimeChatDemoUseCase>(
      ContainerTokens.GetRealtimeChatDemoUseCase,
    );
  }
  get jobsConsoleApi(): JobsConsoleApi {
    return this.resolve<JobsConsoleApi>(ContainerTokens.JobsConsoleApi);
  }
  get jobsConsoleRepository(): JobsConsoleRepository {
    return this.resolve<JobsConsoleRepository>(ContainerTokens.JobsConsoleRepository);
  }
  get getJobsConsoleDemoUseCase(): GetJobsConsoleDemoUseCase {
    return this.resolve<GetJobsConsoleDemoUseCase>(
      ContainerTokens.GetJobsConsoleDemoUseCase,
    );
  }

  get errorsExplorerApi(): ErrorsExplorerApi {
    return this.resolve<ErrorsExplorerApi>(ContainerTokens.ErrorsExplorerApi);
  }

  get errorsExplorerRepository(): ErrorsExplorerRepository {
    return this.resolve<ErrorsExplorerRepository>(ContainerTokens.ErrorsExplorerRepository);
  }

  get getErrorsExplorerDemoUseCase(): GetErrorsExplorerDemoUseCase {
    return this.resolve<GetErrorsExplorerDemoUseCase>(
      ContainerTokens.GetErrorsExplorerDemoUseCase,
    );
  }

  get archTracerApi(): ArchTracerApi {
    return this.resolve<ArchTracerApi>(ContainerTokens.ArchTracerApi);
  }

  get archTracerRepository(): ArchTracerRepository {
    return this.resolve<ArchTracerRepository>(ContainerTokens.ArchTracerRepository);
  }

  get getArchTracerDemoUseCase(): GetArchTracerDemoUseCase {
    return this.resolve<GetArchTracerDemoUseCase>(ContainerTokens.GetArchTracerDemoUseCase);
  }

  get testingRunnerApi(): TestingRunnerApi {
    return this.resolve<TestingRunnerApi>(ContainerTokens.TestingRunnerApi);
  }

  get testingRunnerRepository(): TestingRunnerRepository {
    return this.resolve<TestingRunnerRepository>(ContainerTokens.TestingRunnerRepository);
  }

  get getTestingRunnerDemoUseCase(): GetTestingRunnerDemoUseCase {
    return this.resolve<GetTestingRunnerDemoUseCase>(
      ContainerTokens.GetTestingRunnerDemoUseCase,
    );
  }

  get envInspectorApi(): EnvInspectorApi {
    return this.resolve<EnvInspectorApi>(ContainerTokens.EnvInspectorApi);
  }

  get envInspectorRepository(): EnvInspectorRepository {
    return this.resolve<EnvInspectorRepository>(ContainerTokens.EnvInspectorRepository);
  }

  get getEnvInspectorDemoUseCase(): GetEnvInspectorDemoUseCase {
    return this.resolve<GetEnvInspectorDemoUseCase>(
      ContainerTokens.GetEnvInspectorDemoUseCase,
    );
  }

  get bestChecklistApi(): BestChecklistApi {
    return this.resolve<BestChecklistApi>(ContainerTokens.BestChecklistApi);
  }

  get bestChecklistRepository(): BestChecklistRepository {
    return this.resolve<BestChecklistRepository>(ContainerTokens.BestChecklistRepository);
  }

  get getBestChecklistDemoUseCase(): GetBestChecklistDemoUseCase {
    return this.resolve<GetBestChecklistDemoUseCase>(
      ContainerTokens.GetBestChecklistDemoUseCase,
    );
  }

  // ---- wiring helpers ----

  /** Register (or replace) a singleton under its token. */
  register(token: symbol, instance: unknown): void {
    this.registry.set(token, instance);
  }

  /** Resolve a singleton; throws loudly when the token was never registered. */
  resolve<T>(token: symbol): T {
    const instance = this.registry.get(token);
    if (instance === undefined) {
      throw new Error(`Dependency "${String(token.description)}" is not registered`);
    }
    return instance as T;
  }

  /** Test-only: the raw symbol → instance wiring, for wiring assertions. */
  getWiring(): ReadonlyMap<symbol, unknown> {
    return this.registry;
  }

  /** Test-only: tear down registered singletons. */
  dispose(): void {
    this.registry.clear();
  }
}

export const container = new Container();
