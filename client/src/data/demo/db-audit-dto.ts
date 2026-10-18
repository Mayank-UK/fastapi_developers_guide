import {
  type AuditDemo,
  type AuditEventRow,
  type CommittedChange,
  type RolledBackChange,
} from '../../domain/demo/db-audit';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * DbAuditDTO — the wire/transport shapes of the audit proof: the
 * committed half (change + its audit row), the rolled-back half
 * (attempted title, real error, zero rows added), and the growing
 * history.
 */

export type DbAuditDto = AuditDemo;

function eventFromJson(body: unknown): AuditEventRow {
  if (!isRecord(body)) throw new Error('audit event must be an object');
  return {
    id: requiredNumber(body, 'id'),
    occurredAt: requiredString(body, 'occurredAt'),
    actor: requiredString(body, 'actor'),
    action: requiredString(body, 'action'),
    changes: requiredString(body, 'changes'),
  };
}

function committedFromJson(body: unknown): CommittedChange {
  if (!isRecord(body)) throw new Error('committed change must be an object');
  return {
    statusBefore: requiredString(body, 'statusBefore'),
    statusAfter: requiredString(body, 'statusAfter'),
    changeVisible: requiredBoolean(body, 'changeVisible'),
    auditRow: eventFromJson(body.auditRow),
  };
}

function rolledBackFromJson(body: unknown): RolledBackChange {
  if (!isRecord(body)) throw new Error('rolled back change must be an object');
  return {
    attemptedTitle: requiredString(body, 'attemptedTitle'),
    failure: requiredString(body, 'failure'),
    changeVisible: requiredBoolean(body, 'changeVisible'),
    auditRowsAdded: requiredNumber(body, 'auditRowsAdded'),
  };
}

/** Deserialize + validate the audit payload (both halves + history). */
export function dbAuditFromJson(body: unknown): DbAuditDto {
  if (!isRecord(body)) throw new Error('audit demo must be an object');
  return {
    postId: requiredNumber(body, 'postId'),
    postTitle: requiredString(body, 'postTitle'),
    committed: committedFromJson(body.committed),
    rolledBack: rolledBackFromJson(body.rolledBack),
    history: requiredArray(body, 'history').map(eventFromJson),
    historyCount: requiredNumber(body, 'historyCount'),
    reasoning: requiredString(body, 'reasoning'),
  };
}
