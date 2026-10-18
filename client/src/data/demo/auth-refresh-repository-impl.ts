import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type {
  RefreshExchangeOutcome,
  RefreshLoginOutcome,
  RefreshPanel,
} from '../../domain/demo/auth-refresh';
import type { AuthRefreshRepository } from '../../domain/demo/auth-refresh-repository';
import type { AuthRefreshApi } from './auth-refresh-api';

/**
 * AuthRefreshRepositoryImpl — adapts the refresh lab API to the domain
 * port. Every thrown transport error (including the 401 envelope a dead
 * family's token produces) is guarded into a Failed Result.
 */
export class AuthRefreshRepositoryImpl implements AuthRefreshRepository {
  private readonly api: AuthRefreshApi;

  constructor(api: AuthRefreshApi) {
    this.api = api;
  }

  panel(): Promise<Result<RefreshPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  login(username: string, password: string): Promise<Result<RefreshLoginOutcome>> {
    return safeRepositoryCall(() => this.api.login(username, password));
  }

  exchange(refreshToken: string): Promise<Result<RefreshExchangeOutcome>> {
    return safeRepositoryCall(() => this.api.exchange(refreshToken));
  }
}
