/**
 * Domain models for the databases-sql topic's audit proof (demo block
 * id `db:audit`) — the client-side shape of GET /api/demo/db/audit.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * Both halves of the in-transaction audit pattern, live: `committed`
 * flips a post's status and reads its audit row back from audit_log;
 * `rolledBack` writes an audit row and then trips the title CHECK in
 * the SAME transaction — zero audit rows added, change invisible. The
 * post's full history grows by one row per run.
 */

/** One audit_log row as the history query reads it back. */
export interface AuditEventRow {
  id: number;
  occurredAt: string;
  actor: string;
  action: string;
  changes: string;
}

/** The committed half: the change is visible and its audit row exists. */
export interface CommittedChange {
  statusBefore: string;
  statusAfter: string;
  changeVisible: boolean;
  auditRow: AuditEventRow;
}

/** The rolled-back half: attempted title, real error, nothing survived. */
export interface RolledBackChange {
  attemptedTitle: string;
  failure: string;
  changeVisible: boolean;
  auditRowsAdded: number;
}

/** The whole audit payload: both halves + the growing history. */
export interface AuditDemo {
  postId: number;
  postTitle: string;
  committed: CommittedChange;
  rolledBack: RolledBackChange;
  history: AuditEventRow[];
  historyCount: number;
  reasoning: string;
}
