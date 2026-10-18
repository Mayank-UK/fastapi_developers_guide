import type {
  FastApiAppInfoData,
  HandlerRegistration,
  RouteEntry,
} from '../../domain/demo/fastapi-app-info';
import {
  isRecord,
  optionalString,
  requiredArray,
  requiredString,
} from '../content/validate';

/**
 * FastApiAppInfoDTO — the wire/transport shape of the app-info payload.
 * Mirrors the domain model 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builds ONLY the listed fields
 * (whitelist) and throws on any shape violation, which parseDto upgrades
 * to an InvalidResponseException. Optional server facts (the docs mounts,
 * which exist only while the app leaves them enabled) are
 * omitted-when-absent by the server — the DTO treats null as invalid,
 * absent as fine, per the family convention.
 */

export type FastApiAppInfoDto = FastApiAppInfoData;

/** Deserialize + validate the /api/demo/fastapi/app-info payload. */
export function fastApiAppInfoDtoFromJson(body: unknown): FastApiAppInfoDto {
  if (!isRecord(body)) throw new Error('app info must be an object');
  const docs = requiredRecord(body, 'docs');
  const stack = requiredRecord(body, 'stack');
  return {
    title: requiredString(body, 'title'),
    version: requiredString(body, 'version'),
    environment: requiredString(body, 'environment'),
    docs: {
      docsUrl: optionalString(docs, 'docsUrl'),
      redocUrl: optionalString(docs, 'redocUrl'),
      openapiUrl: optionalString(docs, 'openapiUrl'),
    },
    stack: {
      fastapi: requiredString(stack, 'fastapi'),
      starlette: requiredString(stack, 'starlette'),
      pydantic: requiredString(stack, 'pydantic'),
    },
    middleware: requiredArray(body, 'middleware').map(nonEmptyString),
    exceptionHandlers: requiredArray(body, 'exceptionHandlers').map(handlerFromJson),
    routes: requiredArray(body, 'routes').map(routeFromJson),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toFastApiAppInfo(dto: FastApiAppInfoDto): FastApiAppInfoData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function requiredRecord(source: Record<string, unknown>, key: string): Record<string, unknown> {
  const value = source[key];
  if (!isRecord(value)) throw new Error(`expected object at "${key}"`);
  return value;
}

function handlerFromJson(body: unknown): HandlerRegistration {
  if (!isRecord(body)) throw new Error('handler registration must be an object');
  return {
    exception: requiredString(body, 'exception'),
    handler: requiredString(body, 'handler'),
  };
}

function routeFromJson(body: unknown): RouteEntry {
  if (!isRecord(body)) throw new Error('route entry must be an object');
  return {
    path: requiredString(body, 'path'),
    methods: requiredArray(body, 'methods').map(nonEmptyString),
    tags: requiredArray(body, 'tags').map(nonEmptyString),
  };
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('list entries must be non-empty strings');
  }
  return value;
}
