import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type {
  BearerResource,
  JwtPanel,
  MintedToken,
  TokenLoginOutcome,
  TokenVerifyOutcome,
} from '../../domain/demo/auth-jwt';
import type { AuthJwtRepository } from '../../domain/demo/auth-jwt-repository';
import type { AuthJwtApi } from './auth-jwt-api';

/**
 * AuthJwtRepositoryImpl — adapts the token lab API to the domain port.
 * Every thrown transport error (including the 401 envelope every non-valid
 * token meets at the protected endpoint) is guarded into a Failed Result.
 */
export class AuthJwtRepositoryImpl implements AuthJwtRepository {
  private readonly api: AuthJwtApi;

  constructor(api: AuthJwtApi) {
    this.api = api;
  }

  panel(): Promise<Result<JwtPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  login(username: string, password: string): Promise<Result<TokenLoginOutcome>> {
    return safeRepositoryCall(() => this.api.login(username, password));
  }

  mint(
    username: string,
    scopes: string[],
    ttlSeconds: number,
    notBeforeSeconds: number,
    signWith: 'real' | 'wrong',
  ): Promise<Result<MintedToken>> {
    return safeRepositoryCall(() =>
      this.api.mint(username, scopes, ttlSeconds, notBeforeSeconds, signWith),
    );
  }

  verify(token: string): Promise<Result<TokenVerifyOutcome>> {
    return safeRepositoryCall(() => this.api.verify(token));
  }

  protectedResource(token: string): Promise<Result<BearerResource>> {
    return safeRepositoryCall(() => this.api.protectedResource(token));
  }
}
