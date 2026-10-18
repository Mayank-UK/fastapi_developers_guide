/**
 * Domain models for the validation topic's arena (demo block id
 * `validation:arena`) — the client-side shape of the /api/demo/validation/
 * arena endpoints. Field names match the server's camelCase wire contract
 * 1:1. The demo's subject is real validation made observable: the caller
 * picks one of the roster's REAL wire models and supplies candidate field
 * values; the server runs that model's own pydantic validation and reports
 * per-field outcomes — accepted, coerced (original → coerced), or rejected
 * with the exact {loc, msg, type} triple the 422 validation_failed envelope
 * would carry, `body`-prefixed the way FastAPI reports a request model.
 */

/** The roster choice — mirrors the server's Literal, so bogus keys are dead. */
export type ArenaModelKey = 'note-create' | 'lab-specimen' | 'scenario-patch';

export const ARENA_MODEL_KEYS: readonly ArenaModelKey[] = [
  'note-create',
  'lab-specimen',
  'scenario-patch',
];

/** One field of a roster model: wire name, rule text, required-ness. */
export interface ArenaFieldSpec {
  name: string;
  rule: string;
  required: boolean;
}

/** One roster contender: the real class name, its module, its fields. */
export interface ArenaModelSummary {
  key: ArenaModelKey;
  model: string;
  source: string;
  description: string;
  fields: ArenaFieldSpec[];
}

/** What one candidate carried: type name + capped repr. */
export interface ArenaReceived {
  type: string;
  repr: string;
}

/**
 * One field's verdict from the real pydantic run — discriminated on
 * `status` exactly like the server's wire discrimination.
 */
export type ArenaOutcome =
  | { status: 'accepted'; value: unknown; valueType: string }
  | {
      status: 'coerced';
      original: unknown;
      originalType: string;
      value: unknown;
      valueType: string;
    }
  | { status: 'rejected'; loc: string[]; msg: string; type: string }
  | { status: 'absent'; default?: unknown };

/** One roster field judged against the candidates. */
export interface ArenaFieldRow {
  field: string;
  rule: string;
  required: boolean;
  received?: ArenaReceived;
  outcome: ArenaOutcome;
}

/** One rejection, normalized like the 422 envelope's details triples. */
export interface ArenaError {
  loc: string[];
  msg: string;
  type: string;
}

/** Wire shape of GET /api/demo/validation/arena/roster. */
export interface ArenaRoster {
  models: ArenaModelSummary[];
  /** One paragraph explaining the roster, server-authored. */
  reasoning: string;
}

/** Wire shape of POST /api/demo/validation/arena. */
export interface ArenaVerdict {
  model: ArenaModelSummary;
  roster: ArenaModelSummary[];
  rows: ArenaFieldRow[];
  verdict: 'accepted' | 'rejected';
  /** Accepted rounds only: the validated model dump (wire-spelled keys). */
  validated?: Record<string, unknown>;
  /** Rejected rounds only: the exact envelope triples. */
  errors?: ArenaError[];
  extraKeysIgnored: string[];
  reasoning: string;
}

/** The POST body of one arena round. */
export interface ArenaRound {
  model: ArenaModelKey;
  candidates: Record<string, unknown>;
}
