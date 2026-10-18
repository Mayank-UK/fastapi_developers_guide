import type { Result } from '../../core/result';
import type { BearerResource } from './auth-jwt';
import type {
  AuthorizeOutcome,
  ExchangeOutcome,
  OAuthPanel,
  PkcePair,
} from './auth-oauth';
import type { AuthOauthRepository } from './auth-oauth-repository';

/**
 * GetAuthOauthDemoUseCase — the OAuth lab's use case: the pkce pair, the
 * authorize step, the exchange (right and wrong verifier alike — the
 * failed exchange is half the lesson), and the protected resource.
 */
export class GetAuthOauthDemoUseCase {
  private readonly repository: AuthOauthRepository;

  constructor(repository: AuthOauthRepository) {
    this.repository = repository;
  }

  /** The flow's map: the registered client and its four steps. */
  panel(): Promise<Result<OAuthPanel>> {
    return this.repository.panel();
  }

  /** Generate a verifier/challenge pair (S256) as a client would. */
  pkce(): Promise<Result<PkcePair>> {
    return this.repository.pkce();
  }

  /** The authorize step: consent + the one-time code in the redirect. */
  authorize(challenge: string): Promise<Result<AuthorizeOutcome>> {
    return this.repository.authorize(challenge);
  }

  /** The exchange: code + verifier → access token (wrong verifier → 401). */
  exchange(code: string, verifier: string): Promise<Result<ExchangeOutcome>> {
    return this.repository.exchange(code, verifier);
  }

  /** The resource the exchanged token unlocks (with the scope check). */
  protectedResource(token: string): Promise<Result<BearerResource>> {
    return this.repository.protectedResource(token);
  }
}
