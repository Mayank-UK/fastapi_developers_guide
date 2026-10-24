import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { ArchSagaPanel } from '../../domain/demo/arch-saga';
import type { ArchSagaRepository } from '../../domain/demo/arch-saga-repository';
import type { ArchSagaApi } from './arch-saga-api';

/**
 * ArchSagaRepositoryImpl — adapts the saga API to the domain port. A
 * Failed Result means the panel itself broke (network down,
 * unparseable body); the run's own failure rows arrive as DATA, not as
 * failures — a compensated saga is the demo working.
 */
export class ArchSagaRepositoryImpl implements ArchSagaRepository {
  private readonly api: ArchSagaApi;

  constructor(api: ArchSagaApi) {
    this.api = api;
  }

  saga(): Promise<Result<ArchSagaPanel>> {
    return safeRepositoryCall(() => this.api.saga());
  }
}
