import type {
  ClassificationRow,
  CustomerRecord,
  EraseProof,
  ExportedSubject,
  MaskLevel,
  MaskedSubject,
  PiiFieldView,
  PiiPanel,
  ResetOutcome,
  RoleMaskRow,
  SubjectRow,
} from '../../domain/demo/security-pii';
import { isRecord, requiredArray, requiredNumber, requiredString } from '../content/validate';

/**
 * SecurityPiiDTO — the wire/transport shapes of the PII lab: the panel
 * (subjects, classification catalog, role→mask levels), one masked
 * subject view, the raw export, the erasure proof, and the reset row.
 * Optional halves (the caller's role) ride the wire as null when
 * absent-on-purpose; the DTO treats those nulls as honest absence.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function maskLevelFrom(source: Record<string, unknown>, key: string): MaskLevel {
  const value = source[key];
  if (value !== 'none' && value !== 'partial' && value !== 'full') {
    throw new Error(`expected 'none', 'partial', or 'full': ${key}`);
  }
  return value;
}

function subjectRowFromJson(value: unknown): SubjectRow {
  if (!isRecord(value)) throw new Error('subject row must be an object');
  return {
    customerId: requiredString(value, 'customerId'),
    country: requiredString(value, 'country'),
  };
}

function classificationRowFromJson(value: unknown): ClassificationRow {
  if (!isRecord(value)) throw new Error('classification row must be an object');
  return {
    field: requiredString(value, 'field'),
    category: requiredString(value, 'category'),
    tier: requiredString(value, 'tier'),
    allowsPartial: value['allowsPartial'] === true,
    rationale: requiredString(value, 'rationale'),
  };
}

function roleMaskRowFromJson(value: unknown): RoleMaskRow {
  if (!isRecord(value)) throw new Error('role mask row must be an object');
  return {
    role: requiredString(value, 'role'),
    maskLevel: maskLevelFrom(value, 'maskLevel'),
    note: requiredString(value, 'note'),
  };
}

function fieldViewFromJson(value: unknown): PiiFieldView {
  if (!isRecord(value)) throw new Error('field view must be an object');
  return {
    field: requiredString(value, 'field'),
    category: requiredString(value, 'category'),
    tier: requiredString(value, 'tier'),
    value: requiredString(value, 'value'),
    masked: value['masked'] === true,
    applied: maskLevelFrom(value, 'applied'),
  };
}

function customerRecordFromJson(value: unknown): CustomerRecord {
  if (!isRecord(value)) throw new Error('customer record must be an object');
  return {
    customerId: requiredString(value, 'customerId'),
    fullName: requiredString(value, 'fullName'),
    email: requiredString(value, 'email'),
    phone: requiredString(value, 'phone'),
    dateOfBirth: requiredString(value, 'dateOfBirth'),
    nationalId: requiredString(value, 'nationalId'),
    cardNumber: requiredString(value, 'cardNumber'),
    country: requiredString(value, 'country'),
    signupAt: requiredString(value, 'signupAt'),
  };
}

/** Deserialize + validate the PII panel. */
export function piiPanelFromJson(body: unknown): PiiPanel {
  if (!isRecord(body)) throw new Error('pii panel must be an object');
  return {
    subjects: requiredArray(body, 'subjects').map(subjectRowFromJson),
    classification: requiredArray(body, 'classification').map(classificationRowFromJson),
    roleMasks: requiredArray(body, 'roleMasks').map(roleMaskRowFromJson),
    storeCount: requiredNumber(body, 'storeCount'),
    subjectEndpoint: requiredString(body, 'subjectEndpoint'),
    exportEndpoint: requiredString(body, 'exportEndpoint'),
    eraseEndpoint: requiredString(body, 'eraseEndpoint'),
    resetEndpoint: requiredString(body, 'resetEndpoint'),
    minimizationNote: requiredString(body, 'minimizationNote'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate one masked subject view. */
export function maskedSubjectFromJson(body: unknown): MaskedSubject {
  if (!isRecord(body)) throw new Error('masked subject must be an object');
  return {
    customerId: requiredString(body, 'customerId'),
    principal: requiredString(body, 'principal'),
    principalRole: stringOrNull(body, 'principalRole'),
    maskLevel: maskLevelFrom(body, 'maskLevel'),
    fields: requiredArray(body, 'fields').map(fieldViewFromJson),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the admin-gated export. */
export function exportedSubjectFromJson(body: unknown): ExportedSubject {
  if (!isRecord(body)) throw new Error('exported subject must be an object');
  return {
    customerId: requiredString(body, 'customerId'),
    principal: requiredString(body, 'principal'),
    record: customerRecordFromJson(body['record']),
    classification: requiredArray(body, 'classification').map(classificationRowFromJson),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the erasure proof. */
export function eraseProofFromJson(body: unknown): EraseProof {
  if (!isRecord(body)) throw new Error('erase proof must be an object');
  return {
    customerId: requiredString(body, 'customerId'),
    principal: requiredString(body, 'principal'),
    recordsBefore: requiredNumber(body, 'recordsBefore'),
    recordsAfter: requiredNumber(body, 'recordsAfter'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the reset row. */
export function resetOutcomeFromJson(body: unknown): ResetOutcome {
  if (!isRecord(body)) throw new Error('reset outcome must be an object');
  return {
    seeded: requiredNumber(body, 'seeded'),
    detail: requiredString(body, 'detail'),
  };
}
