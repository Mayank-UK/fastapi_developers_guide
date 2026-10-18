import type { Result } from '../../core/result';
import type {
  SessionInspection,
  SessionLoginOutcome,
  SessionLogoutOutcome,
  SessionsPanel,
} from './auth-sessions';

/**
 * AuthSessionsRepository — the domain-facing port for the authentication
 * topic's cookie lab. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 * Four methods, one per lab action: the roster, the login (which sets the
 * real cookie), the authenticated inspection, and the logout.
 */
export interface AuthSessionsRepository {
  /** The roster: the cookie contract + every live session. */
  panel(): Promise<Result<SessionsPanel>>;
  /** Login with username/password; the browser stores the Set-Cookie. */
  login(username: string, password: string): Promise<Result<SessionLoginOutcome>>;
  /** The authenticated call: the cookie resolves or the call fails. */
  inspect(): Promise<Result<SessionInspection>>;
  /** Logout: the server row is deleted and the cookie cleared. */
  logout(): Promise<Result<SessionLogoutOutcome>>;
}
