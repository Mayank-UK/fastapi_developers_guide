/**
 * Domain models for the security topic's lab (demo block id `security:lab`)
 * — the client-side shape of the /api/demo/security* endpoints. Field names
 * match the server's camelCase wire contract 1:1.
 *
 * The panel carries the three security surfaces the app really runs: the
 * defensive-header table with the WHY for each entry, the CORS policy (the
 * explicit origin list — never a wildcard beside credentials), and the
 * burner's rate-limit policy. The burn round answers either a remaining
 * budget or the 429 throttle itself — which is the lesson, not an error.
 */

/** One security header: name, the stamped value, and why the app sends it. */
export interface HeaderNoteRow {
  header: string;
  value: string;
  why: string;
}

/** The REAL CORS policy the app runs — the constants the wiring reads. */
export interface CorsPolicyRow {
  allowedOrigins: string[];
  allowCredentials: boolean;
  allowedMethods: string[];
  allowedHeaders: string[];
  preflightMaxAgeS: number;
  misconfigNote: string;
}

/** The burner's real policy: window, budget, keying, and the endpoint. */
export interface RateLimitPolicyRow {
  windowSeconds: number;
  budget: number;
  keying: string;
  burnEndpoint: string;
  whyPublicEndpoints: string;
}

/** Wire shape of GET /api/demo/security — the lab panel's contract. */
export interface SecurityLabPanel {
  headers: HeaderNoteRow[];
  cors: CorsPolicyRow;
  rateLimit: RateLimitPolicyRow;
  reasoning: string;
}

/** What the panel fetch observed on its OWN live response, name → value. */
export interface ObservedHeaders {
  readonly [name: string]: string;
}

/** The panel plus the headers the very fetch that loaded it carried. */
export interface SecurityLabLoad {
  panel: SecurityLabPanel;
  observedHeaders: ObservedHeaders;
}

/** Wire shape of one ALLOWED burn: the budget as it now stands. */
export interface BurnOutcome {
  attempt: number;
  remaining: number;
  limit: number;
  windowSeconds: number;
  detail: string;
}

/** The throttled round — the 429 is the lab's lesson, not a failure. */
export interface BurnThrottled {
  status: 429;
  retryAfterSeconds: number | null;
  message: string;
}

/** One burn round: budget remaining, or the throttle with Retry-After. */
export type BurnResult = { kind: 'allowed'; outcome: BurnOutcome } | { kind: 'throttled'; throttled: BurnThrottled };
