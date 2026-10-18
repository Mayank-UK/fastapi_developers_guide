import type { Result } from '../../core/result';
import type {
  RefreshExchangeOutcome,
  RefreshLoginOutcome,
  RefreshPanel,
} from './auth-refresh';

/**
 * AuthRefreshRepository — the domain-facing port for the authentication
 * topic's refresh lab. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 */
export interface AuthRefreshRepository {
  /** The family board: timelines, statuses, the engine's counters. */
  panel(): Promise<Result<RefreshPanel>>;
  /** Login: family birth — the first refresh token, raw once. */
  login(username: string, password: string): Promise<Result<RefreshLoginOutcome>>;
  /** Exchange: rotate to the next link — or trip the reuse alarm. */
  exchange(refreshToken: string): Promise<Result<RefreshExchangeOutcome>>;
}
