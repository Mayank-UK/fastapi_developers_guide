/**
 * Domain models for the performance topic's bench panel (demo block id
 * `perf:bench`) — the client-side shape of GET /api/demo/perf/bench.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * Every number in the payload was measured on the request that served it:
 * real gzip over the bytes of two payloads this API actually serves, the
 * on-loop vs threadpool hygiene comparison with live probes, uvicorn's
 * auto-selected loop and HTTP parser introspected from the serving
 * process, the engine pool's counters, and the stdlib GC read plus one
 * measured off-loop collection.
 */

/** One real payload × one gzip level, measured. */
export interface CompressionRow {
  payloadId: string;
  payload: string;
  level: number;
  rawBytes: number;
  gzippedBytes: number;
  savedPercent: number;
  encodeMs: number;
  decodeMs: number;
  iterations: number;
}

/** One bounded CPU block, either on the loop or contained in a thread. */
export interface HygieneRow {
  label: string;
  what: string;
  elapsedMs: number;
  loopLagMaxMs: number;
  concurrentHealthMs: number;
  concurrentHealthStatus: number;
  verdict: string;
}

/** One live introspection fact — id, label, and the honest value. */
export interface PerfFactRow {
  id: string;
  label: string;
  value: string;
}

/** One REAL full-collection measurement, run off the loop. */
export interface GcCollectionRow {
  workload: string;
  elapsedMs: number;
  collected: number;
  offLoop: boolean;
  note: string;
}

/** The receipt: a real /api/health measured after the whole bench. */
export interface HealthAfter {
  status: number;
  elapsedMs: number;
}

/** Wire shape of GET /api/demo/perf/bench — the panel's contract. */
export interface PerfBenchPanel {
  compression: CompressionRow[];
  hygiene: HygieneRow[];
  loop: PerfFactRow[];
  pool: PerfFactRow[];
  gcFacts: PerfFactRow[];
  gcCollection: GcCollectionRow;
  healthAfter: HealthAfter;
  honestyNote: string;
}
