/**
 * Domain models for the python-runtime topic's streaming demo — the
 * client-side shape of `GET /api/demo/runtime/streaming`. Field names match
 * the server's camelCase NDJSON lines 1:1 (the DTO is the seam where wire
 * and domain may diverge later).
 */

export type StreamChunkKind = 'open' | 'item' | 'closed';

export interface StreamChunk {
  /** Dense, ordered: 0 = open, 1..N = items, N+1 = closed. */
  seq: number;
  kind: StreamChunkKind;
  label: string;
  /** What the line says about itself (present on open and item lines). */
  detail?: string;
  /** Item count confirmed by the closing line. */
  itemsDelivered?: number;
  /** Measured wall-clock cost of the whole stream (closing line only). */
  totalMs?: number;
}

export interface RuntimeStreamingDemoData {
  /** Every line the stream produced, in arrival order. */
  chunks: StreamChunk[];
}
