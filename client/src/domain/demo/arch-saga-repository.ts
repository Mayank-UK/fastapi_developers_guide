import type { Result } from '../../core/result';
import type { ArchSagaPanel } from './arch-saga';

/**
 * ArchSagaRepository — the domain-facing port for the advanced-
 * architecture topic's saga panel. Demo components depend on this
 * interface only; the HTTP adapter lives in data/demo and is wired at
 * the composition root.
 *
 * The panel is one deterministic 2xx read: the server drove the REAL
 * SagaCoordinator over a fresh scratch ledger on the very request that
 * serves it (the failure is an injected raise inside the step's own
 * effect), so every row here was produced by the pattern running, not
 * narrated.
 */
export interface ArchSagaRepository {
  /** The saga panel: workflow, both runs, balances, durability links. */
  saga(): Promise<Result<ArchSagaPanel>>;
}
