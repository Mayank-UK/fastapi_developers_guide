/**
 * Domain models for the authentication topic's token lab (demo block id
 * `auth:jwt`) — the client-side shape of the /api/demo/auth/jwt* endpoints.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is HS256 end to end: the OAuth2 password form login (bearer out),
 * the mint dials (scopes, TTL, not-before, and the wrong-secret forgery),
 * the verify verdicts (every failure mode classified), and the protected
 * endpoint behind the Bearer guard.
 */

/** One claim of the anatomy table: name and what it asserts. */
export interface ClaimRow {
  claim: string;
  meaning: string;
}

/** Wire shape of GET /api/demo/auth/jwt — the token lab's contract. */
export interface JwtPanel {
  algorithm: string;
  issuer: string;
  defaultTtlSeconds: number;
  claims: ClaimRow[];
  loginEndpoint: string;
  mintEndpoint: string;
  verifyEndpoint: string;
  protectedEndpoint: string;
  reasoning: string;
}

/** Wire shape of POST /api/demo/auth/jwt/login (form-encoded in, bearer out). */
export interface TokenLoginOutcome {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  scope: string;
  username: string;
  detail: string;
}

/** Wire shape of POST /api/demo/auth/jwt/mint — token + decoded anatomy. */
export interface MintedToken {
  token: string;
  header: Record<string, string>;
  payload: Record<string, unknown>;
  signedWith: 'real' | 'wrong';
  expiresAt: string;
  detail: string;
}

/** How a verification ended — every PyJWT failure mode, named. */
export type TokenOutcome = 'valid' | 'expired' | 'not-yet-valid' | 'bad-signature' | 'malformed';

/** Wire shape of POST /api/demo/auth/jwt/verify — classification, no secrets. */
export interface TokenVerifyOutcome {
  outcome: TokenOutcome;
  username: string | null;
  scopes: string[] | null;
  expiresAt: string | null;
  detail: string;
}

/** Wire shape of GET /api/demo/auth/jwt/protected (401s surface as Failures). */
export interface BearerResource {
  username: string;
  scopes: string[];
  via: string;
  detail: string;
}
