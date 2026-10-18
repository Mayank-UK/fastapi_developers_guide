import type { Result } from '../../core/result';
import type { AuditDemo } from './db-audit';

/**
 * DbAuditRepository — the domain-facing port for the databases-sql
 * topic's audit proof demo. Demo components depend on this interface
 * only; the HTTP adapter lives in data/demo and is wired at the
 * composition root. One method, one endpoint: run both halves of the
 * proof (idempotent; the status flip alternates and history grows).
 */
export interface DbAuditRepository {
  /** Run the committed and rolled-back halves; return the evidence. */
  prove(): Promise<Result<AuditDemo>>;
}
