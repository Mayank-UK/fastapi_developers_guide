import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { ArchEventStorePanel } from '../../domain/demo/arch-eventstore';
import type { ArchEventStoreRepository } from '../../domain/demo/arch-eventstore-repository';
import type { ArchEventStoreApi } from './arch-eventstore-api';

/**
 * ArchEventStoreRepositoryImpl — adapts the event-store API to the
 * domain port. A Failed Result means the panel itself broke (network
 * down, unparseable body); the refused stale write arrives as DATA,
 * not as a failure — the conflict is the demo working.
 */
export class ArchEventStoreRepositoryImpl implements ArchEventStoreRepository {
  private readonly api: ArchEventStoreApi;

  constructor(api: ArchEventStoreApi) {
    this.api = api;
  }

  eventstore(): Promise<Result<ArchEventStorePanel>> {
    return safeRepositoryCall(() => this.api.eventstore());
  }
}
