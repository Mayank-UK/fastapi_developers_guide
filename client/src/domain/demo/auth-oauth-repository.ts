import type { Result } from '../../core/result';
import type { BearerResource } from './auth-jwt';
import type {
  AuthorizeOutcome,
  ExchangeOutcome,
  OAuthPanel,
  PkcePair,
} from './auth-oauth';

/**
 * AuthOauthRepository — the domain-facing port for the authentication
 * topic's OAuth lab. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 */
export interface AuthOauthRepository {
  /** The flow's map: the registered client and its four steps. */
  panel(): Promise<Result<OAuthPanel>>;
  /** Generate a verifier/challenge pair (S256) as a client would. */
  pkce(): Promise<Result<PkcePair>>;
  /** The authorize step: consent + the one-time code in the redirect. */
  authorize(challenge: string): Promise<Result<AuthorizeOutcome>>;
  /** The exchange: code + verifier → access token (wrong verifier → 401). */
  exchange(code: string, verifier: string): Promise<Result<ExchangeOutcome>>;
  /** The resource the exchanged token unlocks (with the scope check). */
  protectedResource(token: string): Promise<Result<BearerResource>>;
}
