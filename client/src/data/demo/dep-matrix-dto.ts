import type {
  DepMatrixData,
  DepMatrixRow,
  DepMatrixVerdict,
} from '../../domain/demo/dep-matrix';
import {
  isRecord,
  requiredArray,
  requiredString,
} from '../content/validate';

/**
 * DepMatrixDTO — the wire/transport shape of the dependency-matrix payload.
 * Mirrors the domain models 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builder constructs ONLY the listed
 * fields (whitelist) and throws on any shape violation, which parseDto
 * upgrades to an InvalidResponseException. The verdict union narrows on
 * its value exactly like the server's Literal.
 */

export type DepMatrixDto = DepMatrixData;

/** Deserialize + validate the GET /api/demo/dep/matrix payload. */
export function depMatrixDtoFromJson(body: unknown): DepMatrixDto {
  if (!isRecord(body)) throw new Error('dependency matrix must be an object');
  return {
    rows: requiredArray(body, 'rows').map(rowFromJson),
  };
}

/** Convert the transport DTO into its domain model (identity while 1:1). */
export function toDepMatrix(dto: DepMatrixDto): DepMatrixData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function rowFromJson(body: unknown): DepMatrixRow {
  if (!isRecord(body)) throw new Error('matrix row must be an object');
  return {
    flavor: requiredString(body, 'flavor'),
    label: requiredString(body, 'label'),
    tokens: requiredArray(body, 'tokens').map(nonEmptyString),
    verdict: verdictFromJson(body.verdict),
  };
}

function verdictFromJson(body: unknown): DepMatrixVerdict {
  if (typeof body !== 'string') throw new Error('matrix verdict must be a string');
  switch (body) {
    case 'single':
    case 'same-instance':
    case 'distinct-instances':
    case 'shared-middle':
    case 'threadpool':
    case 'event-loop':
      return body;
    default:
      throw new Error(`unknown matrix verdict "${body}"`);
  }
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('matrix tokens must be non-empty strings');
  }
  return value;
}
