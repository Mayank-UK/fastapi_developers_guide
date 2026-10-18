import type {
  AnnotationRow,
  BoundaryCheck,
  EnforcementRun,
  FieldFaceOff,
  FieldRow,
  OriginArgsRow,
  RuntimeTypesDemoData,
  SymbolHints,
} from '../../domain/demo/runtime-types';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredString,
} from '../content/validate';

/**
 * RuntimeTypesDTO — the wire/transport shape of the runtime-types demo
 * payload. Mirrors the domain model 1:1 (the interface is the seam where
 * wire and domain may diverge); the `fromJson` builds ONLY the listed
 * fields (whitelist) and throws on any shape violation, which parseDto
 * upgrades to an InvalidResponseException.
 */

export type RuntimeTypesDemoDto = RuntimeTypesDemoData;

/** Deserialize + validate the GET /api/demo/py/runtime-types payload. */
export function runtimeTypesDtoFromJson(body: unknown): RuntimeTypesDemoDto {
  if (!isRecord(body)) throw new Error('runtime-types payload must be an object');
  return {
    hintsVsRaw: requiredArray(body, 'hintsVsRaw').map(symbolHintsFromJson),
    originArgs: requiredArray(body, 'originArgs').map(originArgsRowFromJson),
    faceOff: faceOffFromJson(body.faceOff),
    enforcement: enforcementFromJson(body.enforcement),
    boundary: boundaryFromJson(body.boundary),
  };
}

/** Convert a transport DTO into a domain model (identity while 1:1). */
export function toRuntimeTypesDemo(dto: RuntimeTypesDemoDto): RuntimeTypesDemoData {
  return dto;
}

/* ---- nested payload validators (throw on shape violation) ---- */

function symbolHintsFromJson(body: unknown): SymbolHints {
  if (!isRecord(body)) throw new Error('symbol hints must be an object');
  const mode = requiredString(body, 'mode');
  if (mode !== 'deferred' && mode !== 'eager') {
    throw new Error(`unknown symbol-hints mode "${mode}"`);
  }
  return {
    symbol: requiredString(body, 'symbol'),
    mode,
    rows: requiredArray(body, 'rows').map(annotationRowFromJson),
  };
}

function annotationRowFromJson(body: unknown): AnnotationRow {
  if (!isRecord(body)) throw new Error('annotation row must be an object');
  return {
    name: requiredString(body, 'name'),
    raw: requiredString(body, 'raw'),
    resolved: requiredString(body, 'resolved'),
  };
}

function originArgsRowFromJson(body: unknown): OriginArgsRow {
  if (!isRecord(body)) throw new Error('origin/args row must be an object');
  return {
    symbol: requiredString(body, 'symbol'),
    alias: requiredString(body, 'alias'),
    origin: requiredString(body, 'origin'),
    args: requiredArray(body, 'args').map(requiredStringShallow),
  };
}

function requiredStringShallow(body: unknown): string {
  if (typeof body !== 'string' || body === '') {
    throw new Error('origin/args entries must be non-empty strings');
  }
  return body;
}

function faceOffFromJson(body: unknown): FieldFaceOff {
  if (!isRecord(body)) throw new Error('field face-off must be an object');
  return {
    dataclassSymbol: requiredString(body, 'dataclassSymbol'),
    dataclassFields: requiredArray(body, 'dataclassFields').map(fieldRowFromJson),
    pydanticSymbol: requiredString(body, 'pydanticSymbol'),
    pydanticFields: requiredArray(body, 'pydanticFields').map(fieldRowFromJson),
  };
}

function fieldRowFromJson(body: unknown): FieldRow {
  if (!isRecord(body)) throw new Error('field row must be an object');
  return {
    name: requiredString(body, 'name'),
    annotation: requiredString(body, 'annotation'),
    required: requiredBoolean(body, 'required'),
  };
}

function enforcementFromJson(body: unknown): EnforcementRun {
  if (!isRecord(body)) throw new Error('enforcement run must be an object');
  return {
    function: requiredString(body, 'function'),
    signature: requiredString(body, 'signature'),
    call: requiredString(body, 'call'),
    declaredReturn: requiredString(body, 'declaredReturn'),
    actualReturn: requiredString(body, 'actualReturn'),
    returnedValue: requiredString(body, 'returnedValue'),
    mypyVerdict: requiredString(body, 'mypyVerdict'),
  };
}

function boundaryFromJson(body: unknown): BoundaryCheck {
  if (!isRecord(body)) throw new Error('boundary check must be an object');
  return {
    model: requiredString(body, 'model'),
    badInput: requiredString(body, 'badInput'),
    outcome: requiredString(body, 'outcome'),
    errorType: requiredString(body, 'errorType'),
    message: requiredString(body, 'message'),
  };
}
