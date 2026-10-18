import type { Result } from '../../core/result';
import type {
  BearerResource,
  JwtPanel,
  MintedToken,
  TokenLoginOutcome,
  TokenVerifyOutcome,
} from './auth-jwt';

/**
 * AuthJwtRepository — the domain-facing port for the authentication
 * topic's token lab. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 */
export interface AuthJwtRepository {
  /** The anatomy: algorithm, issuer, the claim set, the endpoints. */
  panel(): Promise<Result<JwtPanel>>;
  /** The OAuth2 password form flow: credentials in, bearer token out. */
  login(username: string, password: string): Promise<Result<TokenLoginOutcome>>;
  /** Mint with the dials: scopes, ttl, not-before, wrong-secret forgery. */
  mint(
    username: string,
    scopes: string[],
    ttlSeconds: number,
    notBeforeSeconds: number,
    signWith: 'real' | 'wrong',
  ): Promise<Result<MintedToken>>;
  /** Verify any token: every failure mode classified. */
  verify(token: string): Promise<Result<TokenVerifyOutcome>>;
  /** The protected resource behind the Bearer guard. */
  protectedResource(token: string): Promise<Result<BearerResource>>;
}
