import type { Result } from '../../core/result';
import type { BestChecklistPanel } from './best-checklist';

/**
 * BestChecklistRepository — the domain-facing port for the best-practices
 * self-audit. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 *
 * The panel is one live read of the running app's own audit; there is no
 * write path — a self-audit that could be edited would not be one.
 */
export interface BestChecklistRepository {
  /** The audit: ten areas of verdicted rows, the not-does, the score line. */
  panel(): Promise<Result<BestChecklistPanel>>;
}
