import type { Result } from '../../core/result';
import type { ArchSagaPanel } from './arch-saga';
import type { ArchSagaRepository } from './arch-saga-repository';

/**
 * GetArchSagaDemoUseCase — the advanced-architecture topic's saga
 * panel: one read where the server drives the real compensating-
 * transaction coordinator through both of a saga's lives — the
 * committed four-step run, then the failing run whose compensations
 * unwound the completed steps newest-first with ledger proof.
 */
export class GetArchSagaDemoUseCase {
  private readonly repository: ArchSagaRepository;

  constructor(repository: ArchSagaRepository) {
    this.repository = repository;
  }

  /** The saga panel: workflow, both runs, balances, durability links. */
  saga(): Promise<Result<ArchSagaPanel>> {
    return this.repository.saga();
  }
}
