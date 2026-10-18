/**
 * Domain models for the authentication topic's cookie lab (demo block id
 * `auth:sessions`) — the client-side shape of the /api/demo/auth/sessions*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is the server-side session pattern: login answers the cookie
 * instruction the browser will carry (HttpOnly, SameSite=Lax set for real),
 * /me resolves the sealed cookie to the live session row or degrades to the
 * shared failure panel (the 401 envelope), and logout deletes the row so any
 * copy of the old cookie is dead.
 */

/** What the router must put in Set-Cookie — the service's one output. */
export interface CookieInstruction {
  name: string;
  value: string;
  maxAgeSeconds: number;
  path: string;
  httponly: boolean;
  samesite: 'lax' | 'strict' | 'none';
  secure: boolean;
}

/** One live session as the roster shows it — preview, user, expiry. */
export interface SessionRosterEntry {
  sessionIdPreview: string;
  username: string;
  displayName: string;
  issuedAt: string;
  expiresAt: string;
}

/** Wire shape of GET /api/demo/auth/sessions — the cookie lab's state. */
export interface SessionsPanel {
  cookieName: string;
  cookiePath: string;
  maxAgeSeconds: number;
  flagsSet: string[];
  secureNote: string;
  sealNote: string;
  activeSessions: SessionRosterEntry[];
  loginEndpoint: string;
  meEndpoint: string;
  logoutEndpoint: string;
  reasoning: string;
}

/** Wire shape of POST /api/demo/auth/sessions/login. */
export interface SessionLoginOutcome {
  username: string;
  displayName: string;
  scopes: string[];
  cookie: CookieInstruction;
  cookieValueAnatomy: string;
  detail: string;
}

/** Wire shape of GET /api/demo/auth/sessions/me (401s surface as Failures). */
export interface SessionInspection {
  sessionIdPreview: string;
  username: string;
  displayName: string;
  scopes: string[];
  issuedAt: string;
  expiresAt: string;
  detail: string;
}

/** Wire shape of POST /api/demo/auth/sessions/logout. */
export interface SessionLogoutOutcome {
  revoked: boolean;
  cookie: CookieInstruction;
  detail: string;
}
