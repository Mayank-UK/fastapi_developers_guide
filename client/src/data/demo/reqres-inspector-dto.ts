import type {
  ClientAddress,
  QueryParamView,
  RequestInspectorData,
  SeenHeader,
} from '../../domain/demo/reqres-inspector';
import {
  isRecord,
  optionalNumber,
  optionalString,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * ReqresInspectorDTO — the wire/transport shape of the inspector payload.
 * Mirrors the domain model 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builds ONLY the listed fields
 * (whitelist) and throws on any shape violation, which parseDto upgrades
 * to an InvalidResponseException. Request-conditional facts (rawQuery,
 * contentType, contentLength, bodyMessage, client) are omitted-when-absent
 * by the server — the DTO treats null as invalid, absent as fine, per the
 * family convention — while queryParams/headers are always present
 * (possibly empty arrays).
 */

export type ReqresInspectorDto = RequestInspectorData;

/** Deserialize + validate the /api/demo/reqres/inspector payload. */
export function reqresInspectorDtoFromJson(body: unknown): ReqresInspectorDto {
  if (!isRecord(body)) throw new Error('request inspector must be an object');
  return {
    method: requiredString(body, 'method'),
    path: requiredString(body, 'path'),
    rawQuery: optionalString(body, 'rawQuery'),
    queryParams: requiredArray(body, 'queryParams').map(queryParamFromJson),
    headers: requiredArray(body, 'headers').map(seenHeaderFromJson),
    contentType: optionalString(body, 'contentType'),
    contentLength: optionalNumber(body, 'contentLength'),
    bodyMessage: optionalString(body, 'bodyMessage'),
    client: optionalClient(body),
    requestId: requiredString(body, 'requestId'),
    requestIdHeader: requiredString(body, 'requestIdHeader'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toReqresInspector(dto: ReqresInspectorDto): RequestInspectorData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function queryParamFromJson(body: unknown): QueryParamView {
  if (!isRecord(body)) throw new Error('query parameter must be an object');
  return {
    name: requiredString(body, 'name'),
    values: requiredArray(body, 'values').map(nonEmptyString),
    isRepeated: requiredBoolean(body, 'isRepeated'),
  };
}

function seenHeaderFromJson(body: unknown): SeenHeader {
  if (!isRecord(body)) throw new Error('seen header must be an object');
  return {
    name: requiredString(body, 'name'),
    value: requiredString(body, 'value'),
  };
}

function optionalClient(body: Record<string, unknown>): ClientAddress | undefined {
  const raw = body['client'];
  if (raw === undefined) return undefined;
  if (!isRecord(raw)) throw new Error('client must be an object');
  return {
    host: requiredString(raw, 'host'),
    port: requiredNumber(raw, 'port'),
  };
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('value lists must be non-empty strings');
  }
  return value;
}
