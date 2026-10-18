import { type SearchDemo, type SearchMatch } from '../../domain/demo/db-search';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * DbSearchDTO — the wire/transport shapes of the search lab. Plans are
 * plain string arrays (one EXPLAIN output line per entry).
 */

export type DbSearchDto = SearchDemo;

function matchFromJson(body: unknown): SearchMatch {
  if (!isRecord(body)) throw new Error('search match must be an object');
  return {
    id: requiredNumber(body, 'id'),
    slug: requiredString(body, 'slug'),
    title: requiredString(body, 'title'),
    rank: requiredNumber(body, 'rank'),
    headline: requiredString(body, 'headline'),
  };
}

function planLine(value: unknown, index: number): string {
  if (typeof value !== 'string') {
    throw new Error(`expected plan line at ${index}`);
  }
  return value;
}

/** Deserialize + validate the search payload (query, matches, plans). */
export function dbSearchFromJson(body: unknown): DbSearchDto {
  if (!isRecord(body)) throw new Error('search demo must be an object');
  return {
    query: requiredString(body, 'query'),
    parsedQuery: requiredString(body, 'parsedQuery'),
    sql: requiredString(body, 'sql'),
    matchCount: requiredNumber(body, 'matchCount'),
    matches: requiredArray(body, 'matches').map(matchFromJson),
    indexedPlan: requiredArray(body, 'indexedPlan').map(planLine),
    naivePlan: requiredArray(body, 'naivePlan').map(planLine),
    planNote: requiredString(body, 'planNote'),
    reasoning: requiredString(body, 'reasoning'),
  };
}
