/**
 * Domain models for the fastapi-fundamentals topic's app-info demo — the
 * client-side shape of GET /api/demo/fastapi/app-info. Field names match
 * the server's camelCase wire contract 1:1 (the DTO is the seam where wire
 * and domain may diverge later). The payload is the serving app
 * introducing itself: identity, environment, docs mounts, the
 * fastapi/starlette/pydantic stack, the registered middleware and
 * exception handlers, and the route table built from the OpenAPI schema.
 */

export interface DocsMounts {
  /** The Swagger UI mount; absent when the app disabled docs. */
  docsUrl?: string;
  /** The ReDoc mount; absent when the app disabled it. */
  redocUrl?: string;
  /** The OpenAPI schema endpoint; absent when the app disabled it. */
  openapiUrl?: string;
}

export interface StackVersions {
  fastapi: string;
  starlette: string;
  pydantic: string;
}

export interface HandlerRegistration {
  /** The exception class a handler is registered for (display name). */
  exception: string;
  /** The handler function's qualified name. */
  handler: string;
}

export interface RouteEntry {
  /** The declared path, parameters in braces (e.g. /api/content/{topicId}). */
  path: string;
  /** Declared methods, uppercased and sorted (e.g. ['GET', 'POST']). */
  methods: string[];
  /** The OpenAPI tags the path's operations carry. */
  tags: string[];
}

export interface FastApiAppInfoData {
  title: string;
  version: string;
  environment: string;
  docs: DocsMounts;
  stack: StackVersions;
  /** Registered user middleware, in registration order. */
  middleware: string[];
  exceptionHandlers: HandlerRegistration[];
  /** The declared API surface, sorted by path. */
  routes: RouteEntry[];
}
