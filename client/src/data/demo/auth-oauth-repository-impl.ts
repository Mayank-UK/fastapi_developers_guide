import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { BearerResource } from '../../domain/demo/auth-jwt';
import type {
  AuthorizeOutcome,
  ExchangeOutcome,
  OAuthPanel,
  PkcePair,
} from '../../domain/demo/auth-oauth';
import type { AuthOauthRepository } from '../../domain/demo/auth-oauth-repository';
import type { AuthOauthApi } from './auth-oauth-api';

/**
 * AuthOauthRepositoryImpl — adapts the OAuth lab API to the domain port.
 * Every thrown transport error (including the 401 envelope a wrong
 * verifier produces at the exchange) is guarded into a Failed Result.
 */
export class AuthOauthRepositoryImpl implements AuthOauthRepository {
  private readonly api: AuthOauthApi;

  constructor(api: AuthOauthApi) {
    this.api = api;
  }

  panel(): Promise<Result<OAuthPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  pkce(): Promise<Result<PkcePair>> {
    return safeRepositoryCall(() => this.api.pkce());
  }

  authorize(challenge: string): Promise<Result<AuthorizeOutcome>> {
    return safeRepositoryCall(() => this.api.authorize(challenge));
  }

  exchange(code: string, verifier: string): Promise<Result<ExchangeOutcome>> {
    return safeRepositoryCall(() => this.api.exchange(code, verifier));
  }

  protectedResource(token: string): Promise<Result<BearerResource>> {
    return safeRepositoryCall(() => this.api.protectedResource(token));
  }
}
