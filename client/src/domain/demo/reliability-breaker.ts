/**
 * Domain models for the reliability topic's breaker panel (demo block id
 * `reliability:breaker`) — the client-side shape of
 * GET /api/demo/reliability/breaker. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * Every verdict in the payload was returned by the real CircuitBreaker
 * substrate on the request that served it: one full cycle (closed → open
 * → half-open → closed) walked over a fresh breaker per run, the open
 * timeout elapsing on an injected clock, and only the dependency's
 * bounded 60ms failure latency as real wall time.
 */

/** One policy or latency fact — id, label, and the honest value. */
export interface BreakerFactRow {
  id: string;
  label: string;
  value: string;
}

/** One step of the walk: the gate's verdict, the call, the evidence. */
export interface BreakerCallRow {
  step: number;
  label: string;
  action: string;
  stateBefore: string;
  admitted: boolean | null;
  isProbe: boolean;
  dependencyTouched: boolean;
  outcome: string;
  elapsedMs: number;
  consecutiveFailures: number;
  retryAfterS: number | null;
  reason: string;
}

/** Wire shape of GET /api/demo/reliability/breaker — the panel's contract. */
export interface BreakerPanel {
  policy: BreakerFactRow[];
  calls: BreakerCallRow[];
  latency: BreakerFactRow[];
  statesVisited: string[];
  stateLine: string;
  honestyNote: string;
}
