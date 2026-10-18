import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type {
  SessionInspection,
  SessionLoginOutcome,
  SessionLogoutOutcome,
  SessionsPanel,
} from '../../domain/demo/auth-sessions';
import type { AuthSessionsRepository } from '../../domain/demo/auth-sessions-repository';
import type { AuthSessionsApi } from './auth-sessions-api';

/**
 * AuthSessionsRepositoryImpl — adapts the cookie lab API to the domain
 * port. Every thrown transport error (including the 401 envelope an
 * unauthenticated /me produces) is guarded by safeRepositoryCall into a
 * Failed Result.
 */
export class AuthSessionsRepositoryImpl implements AuthSessionsRepository {
  private readonly api: AuthSessionsApi;

  constructor(api: AuthSessionsApi) {
    this.api = api;
  }

  panel(): Promise<Result<SessionsPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  login(username: string, password: string): Promise<Result<SessionLoginOutcome>> {
    return safeRepositoryCall(() => this.api.login(username, password));
  }

  inspect(): Promise<Result<SessionInspection>> {
    return safeRepositoryCall(() => this.api.inspect());
  }

  logout(): Promise<Result<SessionLogoutOutcome>> {
    return safeRepositoryCall(() => this.api.logout());
  }
}
