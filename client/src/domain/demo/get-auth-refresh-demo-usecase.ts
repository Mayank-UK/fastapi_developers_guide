import type { Result } from '../../core/result';
import type {
  RefreshExchangeOutcome,
  RefreshLoginOutcome,
  RefreshPanel,
} from './auth-refresh';
import type { AuthRefreshRepository } from './auth-refresh-repository';

/**
 * GetAuthRefreshDemoUseCase — the refresh lab's use case: login starts a
 * family, exchange rotates (or trips the reuse alarm) — the demo keeps the
 * CURRENT token so the rotate button chains and the replay of an old one
 * proves detection.
 */
export class GetAuthRefreshDemoUseCase {
  private readonly repository: AuthRefreshRepository;

  constructor(repository: AuthRefreshRepository) {
    this.repository = repository;
  }

  /** The family board: timelines, statuses, the engine's counters. */
  panel(): Promise<Result<RefreshPanel>> {
    return this.repository.panel();
  }

  /** Login: family birth — the first refresh token, raw once. */
  login(username: string, password: string): Promise<Result<RefreshLoginOutcome>> {
    return this.repository.login(username, password);
  }

  /** Exchange: rotate to the next link — or trip the reuse alarm. */
  exchange(refreshToken: string): Promise<Result<RefreshExchangeOutcome>> {
    return this.repository.exchange(refreshToken);
  }
}
