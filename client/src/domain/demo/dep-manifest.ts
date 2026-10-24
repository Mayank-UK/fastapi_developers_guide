/**
 * Domain models for the dependency-management topic's manifest panel (demo
 * block id `deps:manifest`) — the client-side shape of GET /api/demo/deps.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The panel is one live parse of the server's REAL pyproject.toml +
 * uv.lock: the two dependency groups (runtime main vs dev tooling), every
 * direct dependency's manifest range beside the lock's exact pin with an
 * honest satisfied/not-judged verdict, a manifest/lock agreement
 * cross-check, a fastapi-rooted direct-vs-transitive tree slice, and
 * whole-lock counts. When either file is unreadable the server degrades
 * to `available: false` with a reason — the panel claims nothing it did
 * not parse.
 */

/** Which manifest block declared the dependency. */
export type DepGroup = 'main' | 'dev';

/** One declared group: where it lives and what installing it means. */
export interface GroupRow {
  group: DepGroup;
  title: string;
  declaredIn: string;
  directCount: number;
  note: string;
}

/** One direct dependency: range, pin, verdict, extras. */
export interface DirectDepRow {
  name: string;
  group: DepGroup;
  constraint: string;
  lockedVersion: string;
  satisfies: boolean | null;
  extras: string;
}

/** One edge of the tree slice: a package the root pulls in. */
export interface TransitiveRow {
  name: string;
  lockedVersion: string;
}

/** The uv-tree view: one root, one level, locked pins all the way. */
export interface TransitiveSlice {
  root: string;
  rootConstraint: string;
  rootLockedVersion: string;
  children: TransitiveRow[];
  note: string;
}

/** The whole lock in three numbers. */
export interface LockCounts {
  totalLocked: number;
  direct: number;
  transitive: number;
  note: string;
}

/** The uv-lock --check spirit, computed: manifest names vs lock names. */
export interface AgreementRow {
  manifestNames: number;
  lockNames: number;
  missingFromLock: string[];
  extraInLock: string[];
  agree: boolean;
}

/** Wire shape of GET /api/demo/deps — the manifest panel's contract. */
export interface DepsManifestPanel {
  manifestFile: string;
  lockFile: string;
  available: boolean;
  unavailableReason: string | null;
  requiresPython: string | null;
  groups: GroupRow[];
  direct: DirectDepRow[];
  slice: TransitiveSlice | null;
  counts: LockCounts | null;
  agreement: AgreementRow | null;
  honestyNote: string;
}
