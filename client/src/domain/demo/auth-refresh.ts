/**
 * Domain models for the authentication topic's refresh lab (demo block id
 * `auth:refresh`) — the client-side shape of the /api/demo/auth/refresh*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is rotation with reuse detection: login starts a family (the raw
 * refresh token appears exactly once), each exchange consumes the presented
 * token and mints the next link, and replaying a used token revokes the
 * whole family — kill count in the response, timelines on the board.
 */

/** One link in a family's timeline — position, status, stamps. */
export interface RefreshTokenRow {
  position: number;
  status: 'active' | 'used' | 'revoked' | string;
  issuedAt: string;
  usedAt: string | null;
}

/** One family: owner, life status, whole token chain. */
export interface RefreshFamily {
  familyId: string;
  username: string;
  status: 'active' | 'revoked' | string;
  createdAt: string;
  tokens: RefreshTokenRow[];
}

/** The engine's in-process counters, snapshot at panel time. */
export interface RefreshTelemetry {
  logins: number;
  rotations: number;
  reuseEvents: number;
}

/** Wire shape of GET /api/demo/auth/refresh — the family board. */
export interface RefreshPanel {
  families: RefreshFamily[];
  telemetry: RefreshTelemetry;
  patternNote: string;
  loginEndpoint: string;
  exchangeEndpoint: string;
  reasoning: string;
}

/** Wire shape of POST /api/demo/auth/refresh/login — family birth. */
export interface RefreshLoginOutcome {
  familyId: string;
  username: string;
  accessToken: string;
  accessExpiresIn: number;
  refreshToken: string;
  detail: string;
}

/** How an exchange ended: rotated, reuse detected, or unknown token. */
export type RefreshOutcome = 'rotated' | 'reuse-detected' | 'invalid';

/** Wire shape of POST /api/demo/auth/refresh/exchange. */
export interface RefreshExchangeOutcome {
  outcome: RefreshOutcome;
  familyId: string | null;
  accessToken: string | null;
  accessExpiresIn: number | null;
  refreshToken: string | null;
  rotatedFromPosition: number | null;
  familyTokensRevoked: number;
  detail: string;
}
