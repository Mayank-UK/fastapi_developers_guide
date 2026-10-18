import {
  type PostPage,
  type PostRecord,
  type PostSort,
  type PostStatus,
  type WorkbenchEnvelope,
  type WorkbenchLayer,
  type WorkbenchOutcome,
  type WorkbenchPagination,
  type WorkbenchRequestFact,
  type WorkbenchRoster,
  type WorkbenchTemplate,
} from '../../domain/demo/posts-workbench';
import {
  isRecord,
  optionalString,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * PostsWorkbenchDTO — the wire/transport shapes of the api-design
 * workbench. Mirrors the domain models 1:1 (the interface is the seam
 * where wire and domain may diverge); the `fromJson` builders construct
 * ONLY the listed fields (whitelist) and throw on any shape violation,
 * which parseDto upgrades to an InvalidResponseException. Optional wire
 * fields (a body, a page, an envelope, a pagination neighbor) stay
 * undefined when the server omitted them — the null-as-invalid rule
 * everywhere in this client.
 */

export type WorkbenchRosterDto = WorkbenchRoster;
export type WorkbenchOutcomeDto = WorkbenchOutcome;

const STATUSES: readonly PostStatus[] = ['draft', 'published'];
const SORTS: readonly PostSort[] = ['newest', 'oldest', 'title'];
const TEMPLATES: readonly WorkbenchTemplate[] = ['/api/posts', '/api/posts/{postId}'];

function enumValue<T extends string>(value: unknown, key: string, allowed: readonly T[]): T {
  if (typeof value !== 'string' || !allowed.includes(value as T)) {
    throw new Error(`expected one of ${allowed.join('|')} at "${key}"`);
  }
  return value as T;
}

function stringList(source: Record<string, unknown>, key: string): string[] {
  return requiredArray(source, key).map((value) => {
    if (typeof value !== 'string' || value === '') {
      throw new Error(`expected a non-empty string in "${key}"`);
    }
    return value;
  });
}

/** Deserialize + validate one stored post. */
export function postRecordFromJson(body: unknown): PostRecord {
  if (!isRecord(body)) throw new Error('post must be an object');
  return {
    id: requiredString(body, 'id'),
    title: requiredString(body, 'title'),
    body: requiredString(body, 'body'),
    author: requiredString(body, 'author'),
    tags: stringList(body, 'tags'),
    status: enumValue(body.status, 'status', STATUSES),
    createdAt: requiredString(body, 'createdAt'),
    updatedAt: requiredString(body, 'updatedAt'),
  };
}

/** Deserialize + validate one collection page. */
export function postPageFromJson(body: unknown): PostPage {
  if (!isRecord(body)) throw new Error('post page must be an object');
  return {
    items: requiredArray(body, 'items').map(postRecordFromJson),
    total: requiredNumber(body, 'total'),
    page: requiredNumber(body, 'page'),
    limit: requiredNumber(body, 'limit'),
    pages: requiredNumber(body, 'pages'),
  };
}

/** Deserialize + validate the request fact (what the round would send). */
export function workbenchRequestFactFromJson(body: unknown): WorkbenchRequestFact {
  if (!isRecord(body)) throw new Error('request fact must be an object');
  const rawBody = body.body;
  return {
    method: requiredString(body, 'method') as WorkbenchRequestFact['method'],
    template: enumValue(body.template, 'template', TEMPLATES),
    path: requiredString(body, 'path'),
    ...(isRecord(rawBody) ? { body: rawBody } : {}),
  };
}

/** Deserialize + validate the failure envelope. */
function workbenchEnvelopeFromJson(body: Record<string, unknown>): WorkbenchEnvelope {
  return {
    code: requiredString(body, 'code'),
    message: requiredString(body, 'message'),
    requestId: requiredString(body, 'requestId'),
  };
}

/** Deserialize + validate the pagination facts (the headers' view). */
function workbenchPaginationFromJson(body: Record<string, unknown>): WorkbenchPagination {
  const next = optionalString(body, 'next');
  const prev = optionalString(body, 'prev');
  return {
    total: requiredNumber(body, 'total'),
    page: requiredNumber(body, 'page'),
    limit: requiredNumber(body, 'limit'),
    pages: requiredNumber(body, 'pages'),
    ...(next === undefined ? {} : { next }),
    ...(prev === undefined ? {} : { prev }),
  };
}

/** Deserialize + validate one pipeline layer row. */
function workbenchLayerFromJson(body: unknown): WorkbenchLayer {
  if (!isRecord(body)) throw new Error('layer must be an object');
  return { name: requiredString(body, 'name'), detail: requiredString(body, 'detail') };
}

/** Deserialize + validate the GET roster payload. */
export function workbenchRosterFromJson(body: unknown): WorkbenchRosterDto {
  if (!isRecord(body)) throw new Error('workbench roster must be an object');
  return {
    authors: stringList(body, 'authors'),
    tags: stringList(body, 'tags'),
    statuses: requiredArray(body, 'statuses').map((value) =>
      enumValue(value, 'statuses', STATUSES),
    ),
    sorts: requiredArray(body, 'sorts').map((value) => enumValue(value, 'sorts', SORTS)),
    totalPosts: requiredNumber(body, 'totalPosts'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the POST outcome payload. */
export function workbenchOutcomeFromJson(body: unknown): WorkbenchOutcomeDto {
  if (!isRecord(body)) throw new Error('workbench outcome must be an object');
  const page = optionalRecordOrUndefined(body, 'page');
  const post = body.post === undefined ? undefined : postRecordFromJson(body.post);
  const envelope =
    body.envelope === undefined
      ? undefined
      : workbenchEnvelopeFromJson(requiredRecord(body, 'envelope'));
  const pagination =
    body.pagination === undefined
      ? undefined
      : workbenchPaginationFromJson(requiredRecord(body, 'pagination'));
  return {
    operation: requiredString(body, 'operation') as WorkbenchOutcome['operation'],
    request: workbenchRequestFactFromJson(requiredRecord(body, 'request')),
    status: requiredNumber(body, 'status'),
    statusReason: requiredString(body, 'statusReason'),
    kind: requiredString(body, 'kind') as WorkbenchOutcome['kind'],
    ...(page === undefined ? {} : { page }),
    ...(post === undefined ? {} : { post }),
    ...(envelope === undefined ? {} : { envelope }),
    ...(pagination === undefined ? {} : { pagination }),
    layers: requiredArray(body, 'layers').map(workbenchLayerFromJson),
    reasoning: requiredString(body, 'reasoning'),
  };
}

function optionalRecordOrUndefined(
  source: Record<string, unknown>,
  key: string,
): PostPage | undefined {
  const value = source[key];
  if (value === undefined) return undefined;
  return postPageFromJson(value);
}
