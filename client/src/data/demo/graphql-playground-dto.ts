import {
  type GraphqlError,
  type GraphqlErrorLocation,
  type GraphqlExample,
  type GraphqlPlayground,
  type GraphqlRunResult,
} from '../../domain/demo/graphql-playground';
import {
  isRecord,
  optionalArray,
  optionalRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * GraphqlPlaygroundDTO — the wire/transport shapes of the graphql
 * console. Mirrors the domain models 1:1 (the interface is the seam
 * where wire and domain may diverge); the `fromJson` builders construct
 * ONLY the listed fields (whitelist) and throw on any shape violation,
 * which parseDto upgrades to an InvalidResponseException.
 *
 * The run result follows the GraphQL over HTTP spec: a response carries
 * `data` and/or `errors` — a 200 with errors is a valid transport of a
 * failed field (the not-found example depends on it), so BOTH shapes
 * validate as success. `data: null` (a total field failure) collapses
 * to just the errors, keeping the domain model honest.
 */

export type GraphqlPlaygroundDto = GraphqlPlayground;
export type GraphqlRunResultDto = GraphqlRunResult;

function graphqlExampleFromJson(body: unknown): GraphqlExample {
  if (!isRecord(body)) throw new Error('graphql example must be an object');
  return {
    id: requiredString(body, 'id'),
    label: requiredString(body, 'label'),
    description: requiredString(body, 'description'),
    query: requiredString(body, 'query'),
  };
}

/** Deserialize + validate the playground package. */
export function graphqlPlaygroundFromJson(body: unknown): GraphqlPlaygroundDto {
  if (!isRecord(body)) throw new Error('graphql playground must be an object');
  return {
    endpoint: requiredString(body, 'endpoint'),
    sdl: requiredString(body, 'sdl'),
    examples: requiredArray(body, 'examples').map(graphqlExampleFromJson),
    reasoning: requiredString(body, 'reasoning'),
  };
}

function errorLocationFromJson(body: unknown): GraphqlErrorLocation {
  if (!isRecord(body)) throw new Error('graphql error location must be an object');
  return {
    line: requiredNumber(body, 'line'),
    column: requiredNumber(body, 'column'),
  };
}

function pathItemFromJson(body: unknown, index: number): string | number {
  if (typeof body === 'string') return body;
  if (typeof body === 'number' && Number.isFinite(body)) return body;
  throw new Error(`graphql error path item ${String(index)} must be a string or number`);
}

function graphqlErrorFromJson(body: unknown): GraphqlError {
  if (!isRecord(body)) throw new Error('graphql error must be an object');
  const locations = optionalArray(body, 'locations')?.map(errorLocationFromJson);
  const rawPath = optionalArray(body, 'path');
  const path = rawPath?.map(pathItemFromJson);
  const extensions = optionalRecord(body, 'extensions');
  return {
    message: requiredString(body, 'message'),
    ...(locations === undefined ? {} : { locations }),
    ...(path === undefined ? {} : { path }),
    ...(extensions === undefined ? {} : { extensions }),
  };
}

/** Deserialize + validate one GraphQL response (data and/or errors). */
export function graphqlRunResultFromJson(body: unknown): GraphqlRunResultDto {
  if (!isRecord(body)) throw new Error('graphql result must be an object');
  const hasData = body.data !== undefined;
  const errors = optionalArray(body, 'errors')?.map(graphqlErrorFromJson);
  if (!hasData && errors === undefined) {
    throw new Error('graphql result must carry data or errors');
  }
  const rawData = body.data;
  if (rawData !== undefined && rawData !== null && !isRecord(rawData)) {
    throw new Error('graphql result data must be an object or null');
  }
  return {
    ...(rawData === undefined || rawData === null ? {} : { data: rawData }),
    ...(errors === undefined ? {} : { errors }),
  };
}
