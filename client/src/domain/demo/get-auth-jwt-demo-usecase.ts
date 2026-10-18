import type { Result } from '../../core/result';
import type {
  BearerResource,
  JwtPanel,
  MintedToken,
  TokenLoginOutcome,
  TokenVerifyOutcome,
} from './auth-jwt';
import type { AuthJwtRepository } from './auth-jwt-repository';

/**
 * GetAuthJwtDemoUseCase — the token lab's use case: the form login, the
 * mint dials (including the wrong-secret forgery), the verify verdicts,
 * and the guarded resource — HS256 end to end.
 */
export class GetAuthJwtDemoUseCase {
  private readonly repository: AuthJwtRepository;

  constructor(repository: AuthJwtRepository) {
    this.repository = repository;
  }

  /** The anatomy: algorithm, issuer, the claim set, the endpoints. */
  panel(): Promise<Result<JwtPanel>> {
    return this.repository.panel();
  }

  /** The OAuth2 password form flow: credentials in, bearer token out. */
  login(username: string, password: string): Promise<Result<TokenLoginOutcome>> {
    return this.repository.login(username, password);
  }

  /** Mint with the dials: scopes, ttl, not-before, wrong-secret forgery. */
  mint(
    username: string,
    scopes: string[],
    ttlSeconds: number,
    notBeforeSeconds: number,
    signWith: 'real' | 'wrong',
  ): Promise<Result<MintedToken>> {
    return this.repository.mint(username, scopes, ttlSeconds, notBeforeSeconds, signWith);
  }

  /** Verify any token: every failure mode classified. */
  verify(token: string): Promise<Result<TokenVerifyOutcome>> {
    return this.repository.verify(token);
  }

  /** The protected resource behind the Bearer guard. */
  protectedResource(token: string): Promise<Result<BearerResource>> {
    return this.repository.protectedResource(token);
  }
}
