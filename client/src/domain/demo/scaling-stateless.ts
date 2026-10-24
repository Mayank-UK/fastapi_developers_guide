/**
 * Domain models for the scaling topic's statelessness panel (demo block id
 * `scaling:stateless`) — the client-side shape of
 * GET /api/demo/scaling/stateless. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * The panel serves the state-placement lesson by introspection: the
 * process facts were snapshot-read off the composition root on the very
 * request that serves them, the two-replica round walks one logical
 * request through two per-replica state worlds (a process-local scenario
 * write that never crosses to the second replica, beside a real redis
 * INCR where the second increment's answer contains the first's), and
 * the inventory places every real store this repo carries.
 */

/** One process or verdict fact — id, label, and the honest value. */
export interface ScalingFactRow {
  id: string;
  label: string;
  value: string;
}

/** One step of the two-replica round: who acted, what happened, what it saw. */
export interface ReplicaStepRow {
  step: number;
  side: string;
  label: string;
  detail: string;
  observed: string;
}

/** One inventory row: a real store this repo carries, placed honestly. */
export interface PlacementRow {
  id: string;
  state: string;
  holder: string;
  placement: string;
  where: string;
  restart: string;
  evidence: string;
}

/** Wire shape of GET /api/demo/scaling/stateless — the panel's contract. */
export interface StatelessPanel {
  process: ScalingFactRow[];
  replicaRound: ReplicaStepRow[];
  verdicts: ScalingFactRow[];
  inventory: PlacementRow[];
  honestyNote: string;
}
