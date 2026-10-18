/**
 * Domain models for the authentication topic's hashing lab (demo block id
 * `auth:hashing`) — the client-side shape of the /api/demo/auth/hashing*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The lab is argon2id with the cost shown honestly: hash mints a fresh
 * salted parameter-stamped string and reports real milliseconds, and verify
 * answers match + needsRehash with the same cost for right and wrong
 * candidates alike.
 */

/** One seeded user's credential facts — hash preview, never the raw. */
export interface SeedCredential {
  username: string;
  displayName: string;
  hashPreview: string;
  scopes: string[];
}

/** Wire shape of GET /api/demo/auth/hashing — argon2's contract. */
export interface HashingPanel {
  algorithm: string;
  parameters: string;
  legacyParameters: string;
  seedCredentials: SeedCredential[];
  distinctionNote: string;
  loggingNote: string;
  hashEndpoint: string;
  verifyEndpoint: string;
  reasoning: string;
}

/** Wire shape of POST /api/demo/auth/hashing/hash — the honest cost. */
export interface PasswordHashOutcome {
  hash: string;
  algorithm: string;
  parameters: string;
  elapsedMs: number;
  detail: string;
}

/** Wire shape of POST /api/demo/auth/hashing/verify — verdict + rehash flag. */
export interface PasswordVerifyOutcome {
  ok: boolean;
  needsRehash: boolean;
  elapsedMs: number;
  error: string | null;
  detail: string;
}
