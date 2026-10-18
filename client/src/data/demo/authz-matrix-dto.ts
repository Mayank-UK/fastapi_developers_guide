import type {
  AuthzCheckOutcome,
  AuthzPanel,
  CheckDecision,
  CheckResource,
  EditedPostOutcome,
  GrantCell,
  ModeratedCommentOutcome,
  PrincipalRow,
  RoleRow,
  SeededCommentRow,
  SeededPostRow,
} from '../../domain/demo/authz-matrix';
import { stringList } from './auth-api-keys-dto';
import { isRecord, requiredArray, requiredString } from '../content/validate';

/**
 * AuthzMatrixDTO — the wire/transport shapes of the matrix lab: the panel
 * (roster + matrix + targets + notes), the what-if check outcome (decision
 * with reason), and the two guarded-endpoint success rows. Optional halves
 * (role, resource) ride the wire as null when absent-on-purpose; the DTO
 * treats those nulls as honest absence, never as a bad field.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function levelOrNull(source: Record<string, unknown>, key: string): 'any' | 'own' | null {
  const value = source[key];
  if (value === null) return null;
  if (value !== 'any' && value !== 'own') throw new Error(`expected 'any', 'own', or null: ${key}`);
  return value;
}

function principalRowFromJson(value: unknown): PrincipalRow {
  if (!isRecord(value)) throw new Error('principal row must be an object');
  const kind = requiredString(value, 'kind');
  if (kind !== 'user' && kind !== 'program') throw new Error(`unknown principal kind: ${kind}`);
  return {
    name: requiredString(value, 'name'),
    displayName: requiredString(value, 'displayName'),
    role: stringOrNull(value, 'role'),
    kind,
    note: requiredString(value, 'note'),
  };
}

function grantCellFromJson(value: unknown): GrantCell {
  if (!isRecord(value)) throw new Error('grant cell must be an object');
  return {
    action: requiredString(value, 'action'),
    level: levelOrNull(value, 'level'),
  };
}

function roleRowFromJson(value: unknown): RoleRow {
  if (!isRecord(value)) throw new Error('role row must be an object');
  return {
    role: requiredString(value, 'role'),
    grants: requiredArray(value, 'grants').map(grantCellFromJson),
  };
}

function seededPostFromJson(value: unknown): SeededPostRow {
  if (!isRecord(value)) throw new Error('seeded post must be an object');
  return {
    id: requiredString(value, 'id'),
    title: requiredString(value, 'title'),
    author: requiredString(value, 'author'),
  };
}

function seededCommentFromJson(value: unknown): SeededCommentRow {
  if (!isRecord(value)) throw new Error('seeded comment must be an object');
  return {
    id: requiredString(value, 'id'),
    postId: requiredString(value, 'postId'),
    author: requiredString(value, 'author'),
    status: requiredString(value, 'status'),
  };
}

function resourceOrNull(source: Record<string, unknown>): CheckResource | null {
  const value = source['resource'];
  if (value === null) return null;
  if (!isRecord(value)) throw new Error('resource must be an object or null');
  return {
    kind: requiredString(value, 'kind'),
    id: requiredString(value, 'id'),
    owner: requiredString(value, 'owner'),
  };
}

/** Deserialize + validate the matrix panel. */
export function authzPanelFromJson(body: unknown): AuthzPanel {
  if (!isRecord(body)) throw new Error('authz panel must be an object');
  return {
    principals: requiredArray(body, 'principals').map(principalRowFromJson),
    roles: requiredArray(body, 'roles').map(roleRowFromJson),
    seededPosts: requiredArray(body, 'seededPosts').map(seededPostFromJson),
    seededComments: requiredArray(body, 'seededComments').map(seededCommentFromJson),
    wildcardScope: requiredString(body, 'wildcardScope'),
    denyNote: requiredString(body, 'denyNote'),
    scopeNote: requiredString(body, 'scopeNote'),
    ownershipNote: requiredString(body, 'ownershipNote'),
    checkEndpoint: requiredString(body, 'checkEndpoint'),
    editPostEndpoint: requiredString(body, 'editPostEndpoint'),
    moderateCommentEndpoint: requiredString(body, 'moderateCommentEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the what-if check outcome. */
export function authzCheckFromJson(body: unknown): AuthzCheckOutcome {
  if (!isRecord(body)) throw new Error('authz check must be an object');
  const decision = body['decision'];
  if (!isRecord(decision)) throw new Error('decision must be an object');
  const verdict: CheckDecision = {
    allowed: decision['allowed'] === true,
    reason: requiredString(decision, 'reason'),
  };
  return {
    principal: requiredString(body, 'principal'),
    role: stringOrNull(body, 'role'),
    scopes: stringList(body, 'scopes'),
    action: requiredString(body, 'action'),
    resource: resourceOrNull(body),
    decision: verdict,
    detail: requiredString(body, 'detail'),
  };
}

function guardedOutcomeFields(source: Record<string, unknown>): {
  principal: string;
  principalKind: 'user' | 'program';
  action: string;
  resourceKind: string;
  resourceId: string;
  reason: string;
  via: string;
  detail: string;
} {
  const kind = requiredString(source, 'principalKind');
  if (kind !== 'user' && kind !== 'program') {
    throw new Error(`unknown principalKind: ${kind}`);
  }
  return {
    principal: requiredString(source, 'principal'),
    principalKind: kind,
    action: requiredString(source, 'action'),
    resourceKind: requiredString(source, 'resourceKind'),
    resourceId: requiredString(source, 'resourceId'),
    reason: requiredString(source, 'reason'),
    via: requiredString(source, 'via'),
    detail: requiredString(source, 'detail'),
  };
}

/** Deserialize + validate the guarded edit's success row. */
export function editedPostFromJson(body: unknown): EditedPostOutcome {
  if (!isRecord(body)) throw new Error('edited post must be an object');
  const post = body['post'];
  if (!isRecord(post)) throw new Error('post must be an object');
  return {
    ...guardedOutcomeFields(body),
    post: {
      id: requiredString(post, 'id'),
      title: requiredString(post, 'title'),
      author: requiredString(post, 'author'),
      body: requiredString(post, 'body'),
      tags: stringList(post, 'tags'),
      status: requiredString(post, 'status'),
    },
  };
}

/** Deserialize + validate the guarded moderation's success row. */
export function moderatedCommentFromJson(body: unknown): ModeratedCommentOutcome {
  if (!isRecord(body)) throw new Error('moderated comment must be an object');
  const comment = body['comment'];
  if (!isRecord(comment)) throw new Error('comment must be an object');
  const moderatedBy = comment['moderatedBy'];
  if (moderatedBy !== null && typeof moderatedBy !== 'string') {
    throw new Error('moderatedBy must be a string or null');
  }
  return {
    ...guardedOutcomeFields(body),
    comment: {
      id: requiredString(comment, 'id'),
      postId: requiredString(comment, 'postId'),
      author: requiredString(comment, 'author'),
      body: requiredString(comment, 'body'),
      status: requiredString(comment, 'status'),
      moderatedBy,
    },
  };
}
