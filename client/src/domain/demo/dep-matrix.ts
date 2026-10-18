/**
 * Domain models for the dependency topic's matrix demo — the client-side
 * shape of GET /api/demo/dep/matrix. Field names match the server's
 * camelCase wire contract 1:1 (the DTO is the seam where wire and domain
 * may diverge later).
 *
 * Each row is one dependency flavor's identity proof: tokens are
 * id()-derived instance identities (or thread names, for the sync row),
 * and the verdict is the machine-checkable fact the tokens establish.
 */

/** What the tokens of one row prove about the framework's caching. */
export type DepMatrixVerdict =
  | 'single'
  | 'same-instance'
  | 'distinct-instances'
  | 'shared-middle'
  | 'threadpool'
  | 'event-loop';

/** One flavor's identity proof. */
export interface DepMatrixRow {
  flavor: string;
  label: string;
  /** Identity tokens in resolution order (thread names for the sync row). */
  tokens: string[];
  verdict: DepMatrixVerdict;
}

/** The whole matrix, as one request resolved it. */
export interface DepMatrixData {
  rows: DepMatrixRow[];
}
