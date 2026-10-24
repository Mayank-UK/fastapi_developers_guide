import type { Result } from '../../core/result';
import type { ArchEventStorePanel } from './arch-eventstore';
import type { ArchEventStoreRepository } from './arch-eventstore-repository';

/**
 * GetArchEventStoreDemoUseCase — the advanced-architecture topic's
 * event-store panel: one read where the server drives the real
 * event-sourcing substrate — append five facts, fold the state back
 * out event by event, rebuild it in a second store, refuse a stale
 * writer — with the mutable-row contrast and the audit_log kinship.
 */
export class GetArchEventStoreDemoUseCase {
  private readonly repository: ArchEventStoreRepository;

  constructor(repository: ArchEventStoreRepository) {
    this.repository = repository;
  }

  /** The event-store panel: history, fold, rebuild, conflict, kinship. */
  eventstore(): Promise<Result<ArchEventStorePanel>> {
    return this.repository.eventstore();
  }
}
