import type { Result } from '../../core/result';
import type {
  SessionInspection,
  SessionLoginOutcome,
  SessionLogoutOutcome,
  SessionsPanel,
} from './auth-sessions';
import type { AuthSessionsRepository } from './auth-sessions-repository';

/**
 * GetAuthSessionsDemoUseCase — the cookie lab's use case (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * The login → /me → logout round is the demo's whole proof, and the
 * browser's cookie jar is part of the pipeline for real.
 */
export class GetAuthSessionsDemoUseCase {
  private readonly repository: AuthSessionsRepository;

  constructor(repository: AuthSessionsRepository) {
    this.repository = repository;
  }

  /** The roster: the cookie contract + every live session. */
  panel(): Promise<Result<SessionsPanel>> {
    return this.repository.panel();
  }

  /** Login with username/password; the browser stores the Set-Cookie. */
  login(username: string, password: string): Promise<Result<SessionLoginOutcome>> {
    return this.repository.login(username, password);
  }

  /** The authenticated call — the cookie resolves or the call fails. */
  inspect(): Promise<Result<SessionInspection>> {
    return this.repository.inspect();
  }

  /** Logout: the server row is deleted and the cookie cleared. */
  logout(): Promise<Result<SessionLogoutOutcome>> {
    return this.repository.logout();
  }
}
