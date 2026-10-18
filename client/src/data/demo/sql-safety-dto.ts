import {
  type PostBrief,
  type SafeQuery,
  type SqlSafety,
  type UnsafeQuery,
} from '../../domain/demo/sql-safety';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * SqlSafetyDTO — the wire/transport shapes of the safety probe.
 * Mirrors the domain models 1:1; the `fromJson` builders construct
 * ONLY the listed fields (whitelist) and throw on any shape violation,
 * which parseDto upgrades to an InvalidResponseException.
 */

export type SqlSafetyDto = SqlSafety;

function postBriefFromJson(body: unknown): PostBrief {
  if (!isRecord(body)) throw new Error('post brief must be an object');
  return {
    id: requiredNumber(body, 'id'),
    slug: requiredString(body, 'slug'),
    title: requiredString(body, 'title'),
    status: requiredString(body, 'status'),
  };
}

function safeFromJson(body: unknown): SafeQuery {
  if (!isRecord(body)) throw new Error('safe query must be an object');
  return {
    sql: requiredString(body, 'sql'),
    parameterName: requiredString(body, 'parameterName'),
    parameterValue: requiredString(body, 'parameterValue'),
    rowCount: requiredNumber(body, 'rowCount'),
    rows: requiredArray(body, 'rows').map(postBriefFromJson),
    note: requiredString(body, 'note'),
  };
}

function unsafeFromJson(body: unknown): UnsafeQuery {
  if (!isRecord(body)) throw new Error('unsafe query must be an object');
  return {
    template: requiredString(body, 'template'),
    renderedSql: requiredString(body, 'renderedSql'),
    executed: requiredBoolean(body, 'executed'),
    why: requiredString(body, 'why'),
  };
}

/** Deserialize + validate the safety payload (both cards). */
export function sqlSafetyFromJson(body: unknown): SqlSafetyDto {
  if (!isRecord(body)) throw new Error('sql safety must be an object');
  return {
    filterValue: requiredString(body, 'filterValue'),
    safe: safeFromJson(body.safe),
    unsafe: unsafeFromJson(body.unsafe),
    wildcardNote: requiredString(body, 'wildcardNote'),
    reasoning: requiredString(body, 'reasoning'),
  };
}
