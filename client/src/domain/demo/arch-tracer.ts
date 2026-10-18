/**
 * Domain models for the architecture topic's tracer (demo block id
 * `arch:tracer`) — the client-side shape of GET /api/demo/arch/tracer.
 * Field names match the server's camelCase wire contract 1:1 (the DTO is
 * the seam where wire and domain may diverge later).
 *
 * The payload is the server's own architecture made observable, split by
 * evidence class: the INTROSPECTED structure (the built middleware stack,
 * the traced route with its real dependency tree, the composition wiring
 * behind the port) and the MEASURED rounds (two real internal requests
 * driven through the app at the ASGI boundary — the ok round crossing
 * every layer, the err round proving the failure path end to end — with
 * timings only on the three boundary beats and every hop labeled by how
 * it is known).
 */

export type StackKind = 'framework' | 'user' | 'router';

export type HopEvidence = 'measured' | 'observed' | 'introspected';

export type BeatName = 'enter' | 'response.start' | 'complete';

export type RoundOutcome = 'ok' | 'err';

export type ProviderKind = 'model' | 'function';

export interface ArchStackLayer {
  /** The layer's class name as mounted (e.g. RequestIdMiddleware). */
  name: string;
  /** Who owns the row: a framework layer, a create_app registration, the router. */
  kind: StackKind;
  /** Request-side position; 0 is outermost (sees the request first). */
  orderIndex: number;
  /** One-line role, server-authored. */
  role: string;
}

export interface ArchDependency {
  /** The handler parameter the provider resolves (e.g. "use_cases"). */
  param: string;
  /** The provider's own name (a model class or a function). */
  provider: string;
  /** A pydantic model provider or a callable function provider. */
  providerKind: ProviderKind;
}

export interface ArchRoute {
  /** The matched path template (e.g. "/api/posts"). */
  template: string;
  /** The traced HTTP method. */
  method: string;
  /** The endpoint function the router dispatched to. */
  endpoint: string;
  /** The declared response_model's name. */
  responseModel: string;
  /** The endpoint's real dependency tree, as FastAPI declared it. */
  dependencies: ArchDependency[];
}

export interface ArchWiring {
  /** The domain port (Protocol) the adapter satisfies. */
  port: string;
  /** The adapter the composition root actually wired. */
  adapter: string;
  /** The use-case bundle published on app.state. */
  useCases: string;
  /** Where the wiring happened. */
  wiredBy: string;
}

export interface ArchBeat {
  /** One measured moment at the ASGI boundary. */
  event: BeatName;
  /** Milliseconds from request-enter (0 for the enter beat itself). */
  offsetMs: number;
}

export interface ArchHop {
  /** The architectural stage (e.g. "repository"). */
  stage: string;
  /** Which layer owns the stage (e.g. "data.adapter"). */
  layer: string;
  /** What happened there, server-authored. */
  detail: string;
  /** How this row is known — never a fabricated timing. */
  evidence: HopEvidence;
}

export interface ArchFact {
  /** A fact's name (e.g. "envelope code"). */
  name: string;
  /** The fact's value, server-stringified. */
  value: string;
}

export interface ArchRound {
  /** Which traced round: the Result success path or the failure path. */
  outcome: RoundOutcome;
  /** The request line as it was driven (e.g. "GET /api/posts?page=2&limit=4"). */
  requestLine: string;
  /** The x-request-id the round sent inbound (the middleware must echo it). */
  inboundRequestId: string;
  /** The round's real HTTP status (200 for ok, 404 for err). */
  status: number;
  /** The three measured boundary beats, in order. */
  beats: ArchBeat[];
  /** Name/value facts read off the round's real response. */
  facts: ArchFact[];
  /** The layer-by-layer story, each row labeled with its evidence. */
  hops: ArchHop[];
}

export interface ArchTracerData {
  /** The built middleware chain, outermost first, the router terminal last. */
  stack: ArchStackLayer[];
  /** The traced endpoint's declared shape. */
  route: ArchRoute;
  /** What the composition root actually wired. */
  wiring: ArchWiring;
  /** The two measured rounds: ok first, err second. */
  rounds: ArchRound[];
  /** One paragraph explaining the tracer's honesty rules, server-authored. */
  reasoning: string;
}
