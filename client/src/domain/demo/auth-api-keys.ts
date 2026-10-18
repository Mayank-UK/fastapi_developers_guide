/**
 * Domain models for the authentication topic's key lab (demo block id
 * `auth:api-keys`) — the client-side shape of the /api/demo/auth/keys*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is the hashed-key lifecycle: generate shows the raw key exactly
 * once (the roster never sees it again), the protected call authenticates
 * the x-api-key header or fails as the 401 envelope, and revoke is an
 * instant prefix-keyed delete.
 */

/** One stored key record as the roster shows it — prefix, hash preview. */
export interface KeyRecord {
  prefix: string;
  name: string;
  scopes: string[];
  keyHashPreview: string;
  createdAt: string;
}

/** Wire shape of GET /api/demo/auth/keys — the key lab's state. */
export interface ApiKeysPanel {
  records: KeyRecord[];
  storageNote: string;
  lookupNote: string;
  createEndpoint: string;
  callEndpoint: string;
  revokeEndpoint: string;
  reasoning: string;
}

/** Wire shape of POST /api/demo/auth/keys — the raw key's ONLY appearance. */
export interface ApiKeyCreated {
  prefix: string;
  key: string;
  keyHash: string;
  name: string;
  scopes: string[];
  detail: string;
}

/** Wire shape of POST /api/demo/auth/keys/call (401s surface as Failures). */
export interface ApiKeyCallOutcome {
  prefix: string;
  name: string;
  scopes: string[];
  detail: string;
}

/** Wire shape of POST /api/demo/auth/keys/revoke (unknown prefix → 404). */
export interface ApiKeyRevokeOutcome {
  prefix: string;
  revoked: boolean;
  detail: string;
}
