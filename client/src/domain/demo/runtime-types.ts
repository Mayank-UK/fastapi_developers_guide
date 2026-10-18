/**
 * Domain models for the python-language topic's runtime-types demo — the
 * client-side shape of `GET /api/demo/py/runtime-types`. Field names match
 * the server's camelCase wire contract 1:1 (the DTO is the seam where wire
 * and domain may diverge later).
 */

export interface AnnotationRow {
  name: string;
  /** The raw `__annotations__` entry (quoted string when deferred). */
  raw: string;
  /** What `typing.get_type_hints` resolves the annotation to. */
  resolved: string;
}

export interface SymbolHints {
  symbol: string;
  mode: 'deferred' | 'eager';
  rows: AnnotationRow[];
}

export interface OriginArgsRow {
  symbol: string;
  alias: string;
  origin: string;
  args: string[];
}

export interface FieldRow {
  name: string;
  annotation: string;
  required: boolean;
}

export interface FieldFaceOff {
  dataclassSymbol: string;
  dataclassFields: FieldRow[];
  pydanticSymbol: string;
  pydanticFields: FieldRow[];
}

export interface EnforcementRun {
  function: string;
  signature: string;
  call: string;
  declaredReturn: string;
  actualReturn: string;
  returnedValue: string;
  mypyVerdict: string;
}

export interface BoundaryCheck {
  model: string;
  badInput: string;
  outcome: string;
  errorType: string;
  message: string;
}

export interface RuntimeTypesDemoData {
  hintsVsRaw: SymbolHints[];
  originArgs: OriginArgsRow[];
  faceOff: FieldFaceOff;
  enforcement: EnforcementRun;
  boundary: BoundaryCheck;
}
