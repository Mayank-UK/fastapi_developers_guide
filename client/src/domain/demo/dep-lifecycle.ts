/**
 * Domain models for the dependency topic's lifecycle demo — the client-side
 * shape of GET /api/demo/dep/lifecycle and GET /api/demo/dep/lifecycle/log.
 * Field names match the server's camelCase wire contract 1:1 (the DTO is
 * the seam where wire and domain may diverge later).
 *
 * The lesson the payload carries: the response confesses what has NOT
 * happened yet (pendingEvents — the teardown runs after these bytes are
 * sent), and the shared span log holds the full ordering
 * setup → handler → response → teardown as sequenced data.
 */

/** One beat of one request span, as the log endpoint serves it. */
export interface DepLifecycleEvent {
  /** Log-wide, strictly increasing — the append order, i.e. the truth. */
  sequence: number;
  spanId: string;
  event: 'setup' | 'handler' | 'response' | 'teardown';
  /** ISO-8601 UTC timestamp of the beat. */
  at: string;
  /** Milliseconds from the span's setup. */
  offsetMs: number;
}

/** The bounded span ring: capacity plus the events it currently holds. */
export interface DepLifecycleLogData {
  capacity: number;
  events: DepLifecycleEvent[];
}

/** What one wrapped request can honestly report about its own span. */
export interface DepLifecycleSpanData {
  spanId: string;
  setupAt: string;
  handlerOffsetMs: number;
  /** Beats that had not run when the body was built: the teardown. */
  pendingEvents: string[];
}
