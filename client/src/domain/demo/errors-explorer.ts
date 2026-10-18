/**
 * Domain models for the exception-handling topic's explorer (demo block id
 * `errors:explorer`) — the client-side shape of the /api/demo/errors*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The panel carries the taxonomy's own facts (eight kinds, statuses,
 * default messages, raise sites, log events); the observed rounds are what
 * the wire actually answered — status, envelope, and the x-request-id
 * header beside it, with a match badge proving they agree.
 */

/** How a kind's trigger fires: a real round, or a recipe with the reason. */
export type TriggerMode = 'live' | 'recipe';

/** One kind's trigger recipe: method, path, optional body/prep, and why. */
export interface TriggerSpec {
  mode: TriggerMode;
  method: string;
  path: string;
  body: string | null;
  prep: string | null;
  note: string;
}

/** One failure kind row: the taxonomy's own facts plus its trigger. */
export interface ErrorKindRow {
  kind: string;
  httpStatus: number;
  defaultMessage: string;
  raisedBy: string;
  loggedAs: string;
  trigger: TriggerSpec;
}

/** The scenario sub-panel: the real GET/PATCH endpoints and the modes. */
export interface ScenarioPanelRow {
  getEndpoint: string;
  patchEndpoint: string;
  modes: string[];
  note: string;
}

/** The probe panel row: endpoint, latency budget, and the three notes. */
export interface ProbePanelRow {
  probeEndpoint: string;
  latencySeconds: number;
  healthyNote: string;
  injectedNote: string;
  latencyNote: string;
}

/** Wire shape of GET /api/demo/errors — the explorer panel's contract. */
export interface ErrorsPanel {
  kinds: ErrorKindRow[];
  envelopeNote: string;
  scenario: ScenarioPanelRow;
  probe: ProbePanelRow;
  reasoning: string;
}

/** The scenario store's current state (GET /api/demo/scenario). */
export interface ScenarioSnapshot {
  dataMode: 'fake' | 'live';
  injectFailure: 'none' | 'error' | 'latency';
}

/** The probe's healthy answer (GET /api/demo/errors/probe on 2xx). */
export interface ProbeOutcome {
  status: string;
  injectFailure: string;
  detail: string;
}

/**
 * One real HTTP round observed as the wire sees it — the failure IS the
 * payload. `code`/`message`/`requestId` come from the parsed envelope;
 * `requestIdHeader` is the response's x-request-id header; the match flag
 * proves they agree. `retryAfterSeconds`, `detailLine`, and `attempts`
 * carry the extras only some kinds produce.
 */
export interface ObservedFailure {
  kind: string;
  httpStatus: number;
  code: string | null;
  message: string | null;
  requestId: string | null;
  requestIdHeader: string | null;
  headerMatchesBody: boolean;
  retryAfterSeconds: number | null;
  detailLine: string | null;
  attempts: number[] | null;
}

/** The inject → 500 → reset → healthy round trip, both halves observed. */
export interface InjectedRound {
  failure: ObservedFailure;
  recovered: ProbeOutcome;
}

/** One probe round: exactly one half is set — healthy outcome or failure. */
export interface ProbeRound {
  outcome: ProbeOutcome | null;
  failure: ObservedFailure | null;
}
