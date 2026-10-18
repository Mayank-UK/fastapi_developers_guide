/**
 * Domain models for the middleware topic's pipeline demo — the client-side
 * shape of GET /api/demo/middleware/pipeline. Field names match the
 * server's camelCase wire contract 1:1 (the DTO is the seam where wire and
 * domain may diverge later). The payload is the middleware chain made
 * observable: the live stack (outermost first, each row classified
 * framework / user / router with its role), a real in-memory pure-ASGI
 * trace proving wrap order (request events descend, the handler runs once,
 * response events unwind in reverse), both derived side orders, and the
 * request id the real RequestIdMiddleware assigned to the very request
 * fetching the payload — echoed on the response's own header.
 */

export type StackKind = 'framework' | 'user' | 'router';

export type TracePhase = 'request' | 'handler' | 'response';

export interface StackLayer {
  /** The layer's class name as mounted (e.g. RequestIdMiddleware). */
  name: string;
  /** Who owns the row: a framework layer, a create_app registration, the router. */
  kind: StackKind;
  /** Request-side position; 0 is outermost (sees the request first). */
  orderIndex: number;
  /** One-line role, server-authored. */
  role: string;
}

export interface TraceEvent {
  /** The stack row that recorded the event. */
  stage: string;
  /** Where in the onion it fired: descending, the terminal app, ascending. */
  phase: TracePhase;
  /** Chronological append order — the ordering proof. */
  sequence: number;
  /** What happened, server-authored. */
  note: string;
}

export interface MiddlewarePipelineData {
  /** The live chain, outermost first, the router terminal last. */
  stack: StackLayer[];
  /** One request replayed through the composition: descend, handler, unwind. */
  trace: TraceEvent[];
  /** Stack names in request order (outermost first). */
  requestSideOrder: string[];
  /** The same names as the response unwinds (innermost first). */
  responseSideOrder: string[];
  /** The id the real middleware assigned to the request fetching this payload. */
  requestId: string;
  /** The header the id rides on ("x-request-id"). */
  requestIdHeader: string;
  /** One paragraph explaining the verdict, server-authored. */
  reasoning: string;
}
