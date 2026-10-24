/**
 * Domain models for the observability topic's trace fan-out (demo block
 * id `obs:trace`) — the client-side shape of GET /api/demo/obs/trace.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The payload is one real fan-out: the server drove three REAL internal
 * requests through the live app (one per outcome class — a clean 200, the
 * posts resource's 404, FastAPI's 422), each carrying an inbound request
 * id DERIVED from the panel request's own id. Every round reports the
 * correlation: the echoed response header, the error envelope's requestId
 * for the failed rounds, and the log rows the round actually produced —
 * the same CapturedEvent shape the viewer panel serves.
 */

import type { CapturedEvent } from './obs-viewer';

/** One real internal request, its outcome, and its correlated log rows. */
export interface TraceRound {
  label: string;
  requestLine: string;
  inboundRequestId: string;
  status: number;
  firstByteMs: number;
  durationMs: number;
  headerEchoed: boolean;
  envelopeCode: string | null;
  envelopeRequestId: string | null;
  logEvents: CapturedEvent[];
  note: string;
}

/** Wire shape of GET /api/demo/obs/trace — the fan-out's contract. */
export interface TraceFanout {
  rootRequestId: string;
  derivedIdConvention: string;
  rounds: TraceRound[];
  correlationNote: string;
  honestyNote: string;
}
