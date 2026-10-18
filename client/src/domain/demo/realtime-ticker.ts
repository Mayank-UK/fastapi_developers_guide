/** Domain types for the realtime ticker demo (demo id `realtime:ticker`). */

/** The stream's fixed facts, as the panel reports them. */
export interface TickerPolicy {
  symbols: string[];
  defaultPaceMs: number;
  retryMs: number;
  keepaliveEvery: number;
  ringCapacity: number;
  mediaType: string;
}

/** The firehose counters, polled while streaming. */
export interface TickerStats {
  ticksSent: number;
  clientsServed: number;
  resumeReplays: number;
  ringRetained: number;
  oldestSeq: number | null;
  newestSeq: number | null;
}

/** One demo endpoint the panel advertises. */
export interface TickerEndpointRow {
  path: string;
  method: string;
  teaches: string;
}

/** GET /api/demo/realtime/ticker — the panel payload. */
export interface TickerPanel {
  policy: TickerPolicy;
  stats: TickerStats;
  endpoints: TickerEndpointRow[];
  honestyNotes: string[];
  reasoning: string;
}

/** One live tick as dispatched by the browser's EventSource. */
export interface TickerTick {
  seq: number;
  symbol: string;
  price: number;
  change: number;
  at: number;
}
