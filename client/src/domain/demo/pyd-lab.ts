/**
 * Domain models for the pydantic topic's validation laboratory — the
 * client-side shape of GET /api/demo/pyd/lab/schema and POST
 * /api/demo/pyd/lab/validate. Field names match the server's camelCase
 * wire contract 1:1 (the DTO is the seam where wire and domain may
 * diverge later). The report is per-field: what the wire carried, what
 * pydantic's lax pipeline made of it, and whether the whole strict
 * specimen validates (including its cross-field rule).
 */

/** What one field actually carried: the JSON type name plus a capped repr. */
export interface PydLabReceived {
  type: string;
  repr: string;
}

/** The raw value already was the target type and value. */
export interface PydLabCleanOutcome {
  status: 'clean';
  value: unknown;
  valueType: string;
}

/** Lax coercion changed the value (or its type) to satisfy the target. */
export interface PydLabCoercedOutcome {
  status: 'coerced';
  value: unknown;
  valueType: string;
  fromType: string;
}

/** The strict target refused the raw value — pydantic's own error type. */
export interface PydLabRejectedOutcome {
  status: 'rejected';
  errorType: string;
  message: string;
}

/** Discriminated on `status`, mirroring the server's FieldOutcome union. */
export type PydLabFieldOutcome =
  | PydLabCleanOutcome
  | PydLabCoercedOutcome
  | PydLabRejectedOutcome;

/** One lab field: the rule applied, the raw input, the outcome. */
export interface PydLabFieldReport {
  field: string;
  rule: string;
  received: PydLabReceived;
  outcome: PydLabFieldOutcome;
}

/** One whole-specimen rejection, normalized like the 422 details. */
export interface PydLabSpecimenError {
  loc: string[];
  msg: string;
  type: string;
}

export interface PydLabReportData {
  rows: PydLabFieldReport[];
  specimenValid: boolean;
  /** The typed, normalized model the submission became; absent when invalid. */
  specimen?: Record<string, unknown>;
  /** Why the specimen was refused; absent when valid. */
  specimenErrors?: PydLabSpecimenError[];
}

export interface PydLabSchemaData {
  model: string;
  /** The generated JSON Schema document (open-shaped, validated as a record). */
  jsonSchema: Record<string, unknown>;
}

/** What the demo component asks for: the edited JSON payload, verbatim. */
export interface PydLabValidateRequest {
  payload: unknown;
}
