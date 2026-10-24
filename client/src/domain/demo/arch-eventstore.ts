/**
 * Domain models for the advanced-architecture topic's event-store
 * panel (demo block id `arch:eventstore`) — the client-side shape of
 * GET /api/demo/arch/eventstore. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * The panel is the real EventStore port end to end: five facts
 * appended with dense versions and stamped clocks, the current state
 * folded back out one event at a time (each fold step its own
 * evidence row), a SECOND store instance replaying the same drafts to
 * a byte-identical state, a stale writer refused totally by the
 * optimistic-concurrency check, the mutable-row contrast, and the
 * audit_log kinship drawn honestly.
 */

/** The store's own identity: port, adapter, stream, event count. */
export interface StoreFactsRow {
  port: string;
  adapter: string;
  stream: string;
  events: number;
}

/** One stored fact: version, type, payload, minted id, clock stamp. */
export interface AppendedEventRow {
  version: number;
  eventType: string;
  payload: string;
  eventId: string;
  occurredAt: string;
}

/** Per-event fold evidence: the state after applying exactly this fact. */
export interface FoldStepRow {
  afterVersion: number;
  eventType: string;
  stateNow: string;
}

/** The optimistic-concurrency proof: the stale write, refused totally. */
export interface ConcurrencyRow {
  writer: string;
  expectedVersion: number;
  actualVersion: number;
  storedEventsAfter: number;
  evidence: string;
}

/** Mutable row vs event stream: what each keeps, what each answers. */
export interface ContrastRow {
  approach: string;
  keeps: string;
  history: string;
  answers: string;
}

/** The repo's nearest relative to an event store, honestly placed. */
export interface KinshipRow {
  relative: string;
  where: string;
  same: string;
  different: string;
}

/** The replay promise's answer: the rebuilt state and the equality flag. */
export interface RebuildRow {
  method: string;
  state: Record<string, unknown>;
  matches: boolean;
  evidence: string;
}

/** Wire shape of GET /api/demo/arch/eventstore — the whole tour in one. */
export interface ArchEventStorePanel {
  store: StoreFactsRow;
  appended: AppendedEventRow[];
  foldSteps: FoldStepRow[];
  currentState: Record<string, unknown>;
  rebuild: RebuildRow;
  concurrency: ConcurrencyRow;
  contrast: ContrastRow[];
  kinship: KinshipRow;
  honestyNote: string;
}
