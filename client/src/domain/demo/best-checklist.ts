/**
 * Domain models for the best-practices self-audit (demo block id
 * `best:checklist`) — the client-side shape of GET /api/demo/best/checklist.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The panel is one live audit of the running app and the repo it lives in:
 * ten practice areas of rows, each row carrying the verdict kind it earned
 * (live probes through the very app, real file reads, or an honest manual
 * that claims nothing), the evidence lines that produced it, and — for
 * manuals — the one-line why. The anti-checklist rides along as the repo's
 * deliberate not-does with reasons and artifacts.
 */

/** How a row was checked: a live self-request, a repo file read, or a human. */
export type CheckKind = 'live' | 'file' | 'manual';

/** pass/fail are machine-judged from evidence; manual claims nothing. */
export type Verdict = 'pass' | 'fail' | 'manual';

/** One practice, one verdict, and the evidence that produced it. */
export interface ChecklistItemRow {
  id: string;
  practice: string;
  checkKind: CheckKind;
  verdict: Verdict;
  evidence: string[];
  whyManual: string | null;
}

/** One practice area: its rows plus a one-line frame for the panel. */
export interface ChecklistAreaRow {
  id: string;
  title: string;
  note: string;
  items: ChecklistItemRow[];
}

/** One deliberate NOT-done: the decision, its reason, its artifacts. */
export interface NotDoneRow {
  id: string;
  notDone: string;
  reason: string;
  artifacts: string[];
}

/** The panel's score line — counts, nothing spun. */
export interface ChecklistSummaryRow {
  items: number;
  passed: number;
  failed: number;
  manual: number;
}

/** Wire shape of GET /api/demo/best/checklist — the self-audit's contract. */
export interface BestChecklistPanel {
  areas: ChecklistAreaRow[];
  notDones: NotDoneRow[];
  summary: ChecklistSummaryRow;
  honestyNote: string;
}
