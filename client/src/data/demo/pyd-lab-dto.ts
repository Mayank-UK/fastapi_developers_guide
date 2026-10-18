import type {
  PydLabFieldOutcome,
  PydLabFieldReport,
  PydLabReceived,
  PydLabReportData,
  PydLabSchemaData,
  PydLabSpecimenError,
} from '../../domain/demo/pyd-lab';
import {
  isRecord,
  optionalArray,
  optionalRecord,
  requiredArray,
  requiredBoolean,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * PydLabDTO — the wire/transport shape of the validation-lab payloads.
 * Mirrors the domain models 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builders construct ONLY the listed
 * fields (whitelist) and throw on any shape violation, which parseDto
 * upgrades to an InvalidResponseException. The outcome union narrows on
 * its `status` discriminator exactly like the server's pydantic union;
 * optional facts (specimen / specimenErrors) are omitted-when-absent by
 * the server — the DTO treats null as invalid, absent as fine, per the
 * family convention.
 */

export type PydLabReportDto = PydLabReportData;
export type PydLabSchemaDto = PydLabSchemaData;

/** Deserialize + validate the GET /api/demo/pyd/lab/schema payload. */
export function pydLabSchemaDtoFromJson(body: unknown): PydLabSchemaDto {
  if (!isRecord(body)) throw new Error('pyd lab schema must be an object');
  return {
    model: requiredString(body, 'model'),
    jsonSchema: requiredRecord(body, 'jsonSchema'),
  };
}

/** Deserialize + validate the POST /api/demo/pyd/lab/validate report. */
export function pydLabReportDtoFromJson(body: unknown): PydLabReportDto {
  if (!isRecord(body)) throw new Error('pyd lab report must be an object');
  return {
    rows: requiredArray(body, 'rows').map(fieldReportFromJson),
    specimenValid: requiredBoolean(body, 'specimenValid'),
    specimen: optionalRecord(body, 'specimen'),
    specimenErrors: optionalArray(body, 'specimenErrors')?.map(specimenErrorFromJson),
  };
}

/** Convert transport DTOs into domain models (identity while 1:1). */
export function toPydLabReport(dto: PydLabReportDto): PydLabReportData {
  return dto;
}

/** Convert the schema DTO into its domain model (identity while 1:1). */
export function toPydLabSchema(dto: PydLabSchemaDto): PydLabSchemaData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function fieldReportFromJson(body: unknown): PydLabFieldReport {
  if (!isRecord(body)) throw new Error('field report must be an object');
  return {
    field: requiredString(body, 'field'),
    rule: requiredString(body, 'rule'),
    received: receivedFromJson(body.received),
    outcome: outcomeFromJson(body.outcome),
  };
}

function receivedFromJson(body: unknown): PydLabReceived {
  if (!isRecord(body)) throw new Error('received value must be an object');
  return {
    type: requiredString(body, 'type'),
    repr: requiredString(body, 'repr'),
  };
}

function outcomeFromJson(body: unknown): PydLabFieldOutcome {
  if (!isRecord(body)) throw new Error('field outcome must be an object');
  const status = requiredString(body, 'status');
  switch (status) {
    case 'clean':
      return { status, value: body.value, valueType: requiredString(body, 'valueType') };
    case 'coerced':
      return {
        status,
        value: body.value,
        valueType: requiredString(body, 'valueType'),
        fromType: requiredString(body, 'fromType'),
      };
    case 'rejected':
      return {
        status,
        errorType: requiredString(body, 'errorType'),
        message: requiredString(body, 'message'),
      };
    default:
      throw new Error(`unknown field outcome status "${status}"`);
  }
}

function specimenErrorFromJson(body: unknown): PydLabSpecimenError {
  if (!isRecord(body)) throw new Error('specimen error must be an object');
  return {
    loc: requiredArray(body, 'loc').map(nonEmptyString),
    msg: requiredString(body, 'msg'),
    type: requiredString(body, 'type'),
  };
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('specimen error loc entries must be non-empty strings');
  }
  return value;
}
