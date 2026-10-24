/**
 * Domain models for the debugging topic's stall diagnosis (demo block
 * id `debug:stall`) — the client-side shape of GET /api/demo/debug/stall.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The payload is one live diagnosis: the server ran four bounded phases
 * (a baseline yield, an async await, a threadpool-contained block, and an
 * on-loop block), each with REAL measurements — elapsed, loop lag from a
 * concurrent probe's sleep overshoot, and a REAL internal /api/health
 * driven through the app mid-phase — plus a genuine tracemalloc window
 * and this request's own correlated log rows. Every duration is bounded
 * by design, so the shared dev loop is never wedged.
 */

import type { CapturedEvent } from './obs-viewer';

/** One phase of the stall diagnosis, with its measured evidence. */
export interface StallPhase {
  label: string;
  what: string;
  elapsedMs: number;
  loopLagMaxMs: number;
  loopLagMeanMs: number;
  concurrentHealthMs: number;
  concurrentHealthStatus: number;
  verdict: string;
}

/** One REAL tracemalloc window around the bounded workload. */
export interface StallAllocations {
  workload: string;
  objects: number;
  currentKb: number;
  peakKb: number;
  note: string;
}

/** Wire shape of GET /api/demo/debug/stall — the panel's contract. */
export interface StallPanel {
  panelRequestId: string;
  phases: StallPhase[];
  allocations: StallAllocations;
  logEvents: CapturedEvent[];
  pySpyNote: string;
  honestyNote: string;
}
