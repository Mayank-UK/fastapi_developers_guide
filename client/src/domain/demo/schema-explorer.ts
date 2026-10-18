/**
 * Domain models for the sql-schema topic's explorer (demo block id
 * `db:schema-explorer`) — the client-side shape of
 * GET /api/demo/db/schema-explorer. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * The payload is the LIVE database introspected as data: the roster
 * lists every public table with its fact counts, and drilling into a
 * table (`?table=`) adds `focus` — the full anatomy (columns with
 * types/nullability/defaults, primary key, foreign keys with ON DELETE
 * behavior, CHECK definitions, every index with kind and partial
 * WHERE). Nothing is canned: a new migration changes this answer.
 */

/** One table as the roster lists it: a name plus its fact counts. */
export interface TableSummary {
  name: string;
  columnCount: number;
  foreignKeyCount: number;
  checkCount: number;
  indexCount: number;
}

/** One column: type as PostgreSQL spells it, nullability, raw default. */
export interface ColumnField {
  name: string;
  type: string;
  nullable: boolean;
  /** Raw server default (e.g. nextval('posts_id_seq'::regclass)); absent when the column has none. */
  defaultValue?: string;
}

/** One foreign key: local columns → referenced columns, ON DELETE. */
export interface ForeignLink {
  name: string;
  columns: string[];
  referencesTable: string;
  referencesColumns: string[];
  onDelete: string;
}

/** One CHECK constraint with its definition verbatim. */
export interface CheckDef {
  name: string;
  definition: string;
}

/** One index: columns, access method, uniqueness, primary-ness, WHERE. */
export interface IndexDef {
  name: string;
  columns: string[];
  kind: string;
  unique: boolean;
  primary: boolean;
  /** Present only for partial indexes — the predicate PostgreSQL stored. */
  where?: string;
}

/** The drill-down: one table's full introspected anatomy. */
export interface TableFocus {
  name: string;
  columns: ColumnField[];
  primaryKey: string[];
  foreignKeys: ForeignLink[];
  checks: CheckDef[];
  indexes: IndexDef[];
}

/** The whole explorer payload: roster, optional focus, reasoning. */
export interface SchemaExplorer {
  databaseName: string;
  tableCount: number;
  tables: TableSummary[];
  /** Present when the request drilled into one table (`?table=`). */
  focus?: TableFocus;
  reasoning: string;
}
