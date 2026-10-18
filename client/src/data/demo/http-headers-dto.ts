import type {
  EchoedHeader,
  HeaderScope,
  HttpHeadersEchoData,
} from '../../domain/demo/http-headers';
import {
  isRecord,
  optionalString,
  requiredArray,
  requiredString,
} from '../content/validate';

/**
 * HttpHeadersDTO — the wire/transport shape of the headers-echo payload.
 * Mirrors the domain model 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builds ONLY the listed fields
 * (whitelist) and throws on any shape violation, which parseDto upgrades to
 * an InvalidResponseException. Optional server facts (query, contentType,
 * bodyMessage, per-header notes) are omitted-when-absent by the server —
 * the DTO treats null as invalid, absent as fine, per the family convention.
 */

export type HttpHeadersDemoDto = HttpHeadersEchoData;

const HEADER_SCOPES: readonly string[] = ['end-to-end', 'hop-by-hop'];

/** Deserialize + validate the /api/demo/http/headers echo payload. */
export function httpHeadersDtoFromJson(body: unknown): HttpHeadersDemoDto {
  if (!isRecord(body)) throw new Error('http headers echo must be an object');
  return {
    method: requiredString(body, 'method'),
    path: requiredString(body, 'path'),
    query: optionalString(body, 'query'),
    contentType: optionalString(body, 'contentType'),
    bodyMessage: optionalString(body, 'bodyMessage'),
    headers: requiredArray(body, 'headers').map(echoedHeaderFromJson),
    hopByHop: requiredArray(body, 'hopByHop').map(nonEmptyString),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toHttpHeadersEcho(dto: HttpHeadersDemoDto): HttpHeadersEchoData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function echoedHeaderFromJson(body: unknown): EchoedHeader {
  if (!isRecord(body)) throw new Error('echoed header must be an object');
  const scope = requiredString(body, 'scope');
  if (!HEADER_SCOPES.includes(scope)) {
    throw new Error(`unknown header scope "${scope}"`);
  }
  return {
    name: requiredString(body, 'name'),
    value: requiredString(body, 'value'),
    scope: scope as HeaderScope,
    note: optionalString(body, 'note'),
  };
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('hop-by-hop entries must be non-empty strings');
  }
  return value;
}
