/**
 * Domain models for the authentication topic's OAuth lab (demo block id
 * `auth:oauth`) — the client-side shape of the /api/demo/auth/oauth*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The lab walks the authorization-code + PKCE grant over the in-repo
 * authorization server: pair → authorize (consent + one-time code in the
 * redirect) → exchange (verifier proved, code burned) → the protected
 * resource. A wrong verifier is a dead code and a 401 — by design.
 */

/** Wire shape of GET /api/demo/auth/oauth — the flow's map. */
export interface OAuthPanel {
  clientId: string;
  clientKind: string;
  redirectUris: string[];
  clientScopes: string[];
  codeTtlSeconds: number;
  pkceNote: string;
  steps: string[];
  pkceEndpoint: string;
  authorizeEndpoint: string;
  tokenEndpoint: string;
  protectedEndpoint: string;
  reasoning: string;
}

/** Wire shape of POST /api/demo/auth/oauth/pkce — a verifier/challenge pair. */
export interface PkcePair {
  verifier: string;
  codeChallenge: string;
  method: 'S256';
  detail: string;
}

/** Wire shape of POST /api/demo/auth/oauth/authorize — the redirect + code. */
export interface AuthorizeOutcome {
  redirectTo: string;
  state: string;
  consent: string;
  codePreview: string;
  expiresIn: number;
  detail: string;
}

/** Wire shape of POST /api/demo/auth/oauth/token — the earned access token. */
export interface ExchangeOutcome {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  scope: string;
  username: string;
  detail: string;
}
