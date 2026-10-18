import type {
  BoundParam,
  MatchOutcome,
  NearMiss,
  ParamSource,
  RequestLine,
  RoutingExplorerData,
} from '../../domain/demo/routing-explorer';
import {
  isRecord,
  optionalArray,
  optionalString,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * RoutingExplorerDTO — the wire/transport shape of the explorer payload.
 * Mirrors the domain model 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builds ONLY the listed fields
 * (whitelist) and throws on any shape violation, which parseDto upgrades
 * to an InvalidResponseException. Outcome-conditional facts (matchedPath,
 * allowedMethods, redirectTarget, nearMisses, …) are omitted-when-absent
 * by the server — the DTO treats null as invalid, absent as fine, per the
 * family convention — while pathParams/queryParams are always present
 * (possibly empty arrays).
 */

export type RoutingExplorerDto = RoutingExplorerData;

const MATCH_OUTCOMES: readonly string[] = [
  'matched',
  'redirect',
  'method_not_allowed',
  'not_found',
];

const PARAM_SOURCES: readonly string[] = ['path', 'query'];

/** Deserialize + validate the /api/demo/routing/explorer payload. */
export function routingExplorerDtoFromJson(body: unknown): RoutingExplorerDto {
  if (!isRecord(body)) throw new Error('routing explorer must be an object');
  return {
    request: requestLineFromJson(requiredRecord(body, 'request')),
    routeCount: requiredNumber(body, 'routeCount'),
    outcome: outcomeFromJson(body),
    reasoning: requiredString(body, 'reasoning'),
    matchedPath: optionalString(body, 'matchedPath'),
    matchedMethods: optionalArray(body, 'matchedMethods')?.map(nonEmptyString),
    matchedTags: optionalArray(body, 'matchedTags')?.map(nonEmptyString),
    pathParams: requiredArray(body, 'pathParams').map(boundParamFromJson),
    queryParams: requiredArray(body, 'queryParams').map(boundParamFromJson),
    allowedMethods: optionalArray(body, 'allowedMethods')?.map(nonEmptyString),
    redirectTarget: optionalString(body, 'redirectTarget'),
    nearMisses: optionalArray(body, 'nearMisses')?.map(nearMissFromJson),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toRoutingExplorer(dto: RoutingExplorerDto): RoutingExplorerData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function requestLineFromJson(body: Record<string, unknown>): RequestLine {
  return {
    method: requiredString(body, 'method'),
    path: requiredString(body, 'path'),
  };
}

function outcomeFromJson(body: Record<string, unknown>): MatchOutcome {
  const outcome = requiredString(body, 'outcome');
  if (!MATCH_OUTCOMES.includes(outcome)) {
    throw new Error(`unknown match outcome "${outcome}"`);
  }
  return outcome as MatchOutcome;
}

function boundParamFromJson(body: unknown): BoundParam {
  if (!isRecord(body)) throw new Error('bound parameter must be an object');
  const source = requiredString(body, 'source');
  if (!PARAM_SOURCES.includes(source)) {
    throw new Error(`unknown parameter source "${source}"`);
  }
  return {
    name: requiredString(body, 'name'),
    value: requiredString(body, 'value'),
    source: source as ParamSource,
  };
}

function nearMissFromJson(body: unknown): NearMiss {
  if (!isRecord(body)) throw new Error('near miss must be an object');
  return {
    path: requiredString(body, 'path'),
    methods: requiredArray(body, 'methods').map(nonEmptyString),
  };
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('list entries must be non-empty strings');
  }
  return value;
}
