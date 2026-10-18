import {
  type CheckDef,
  type ColumnField,
  type ForeignLink,
  type IndexDef,
  type SchemaExplorer,
  type TableFocus,
  type TableSummary,
} from '../../domain/demo/schema-explorer';
import {
  isRecord,
  optionalString,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * SchemaExplorerDTO — the wire/transport shapes of the schema explorer.
 * Mirrors the domain models 1:1 (the interface is the seam where wire
 * and domain may diverge); the `fromJson` builders construct ONLY the
 * listed fields (whitelist) and throw on any shape violation, which
 * parseDto upgrades to an InvalidResponseException. `focus`,
 * `defaultValue`, and `where` are optional wire fields — their absence
 * is data (no drill-down / no default / a full index), so they surface
 * as undefined on the domain model, never as null.
 */

export type SchemaExplorerDto = SchemaExplorer;

function stringItem(body: unknown, index: number): string {
  if (typeof body !== 'string' || body === '') {
    throw new Error(`expected non-empty string at item ${index}`);
  }
  return body;
}

function summaryFromJson(body: unknown): TableSummary {
  if (!isRecord(body)) throw new Error('table summary must be an object');
  return {
    name: requiredString(body, 'name'),
    columnCount: requiredNumber(body, 'columnCount'),
    foreignKeyCount: requiredNumber(body, 'foreignKeyCount'),
    checkCount: requiredNumber(body, 'checkCount'),
    indexCount: requiredNumber(body, 'indexCount'),
  };
}

function columnFromJson(body: unknown): ColumnField {
  if (!isRecord(body)) throw new Error('column must be an object');
  const defaultValue = optionalString(body, 'default');
  return {
    name: requiredString(body, 'name'),
    type: requiredString(body, 'type'),
    nullable: requiredBoolean(body, 'nullable'),
    ...(defaultValue === undefined ? {} : { defaultValue }),
  };
}

function foreignKeyFromJson(body: unknown): ForeignLink {
  if (!isRecord(body)) throw new Error('foreign key must be an object');
  return {
    name: requiredString(body, 'name'),
    columns: requiredArray(body, 'columns').map(stringItem),
    referencesTable: requiredString(body, 'referencesTable'),
    referencesColumns: requiredArray(body, 'referencesColumns').map(stringItem),
    onDelete: requiredString(body, 'onDelete'),
  };
}

function checkFromJson(body: unknown): CheckDef {
  if (!isRecord(body)) throw new Error('check must be an object');
  return {
    name: requiredString(body, 'name'),
    definition: requiredString(body, 'definition'),
  };
}

function indexFromJson(body: unknown): IndexDef {
  if (!isRecord(body)) throw new Error('index must be an object');
  const where = optionalString(body, 'where');
  return {
    name: requiredString(body, 'name'),
    columns: requiredArray(body, 'columns').map(stringItem),
    kind: requiredString(body, 'kind'),
    unique: requiredBoolean(body, 'unique'),
    primary: requiredBoolean(body, 'primary'),
    ...(where === undefined ? {} : { where }),
  };
}

function focusFromJson(body: unknown): TableFocus {
  if (!isRecord(body)) throw new Error('table focus must be an object');
  return {
    name: requiredString(body, 'name'),
    columns: requiredArray(body, 'columns').map(columnFromJson),
    primaryKey: requiredArray(body, 'primaryKey').map(stringItem),
    foreignKeys: requiredArray(body, 'foreignKeys').map(foreignKeyFromJson),
    checks: requiredArray(body, 'checks').map(checkFromJson),
    indexes: requiredArray(body, 'indexes').map(indexFromJson),
  };
}

/** Deserialize + validate the explorer payload (roster, optional focus). */
export function schemaExplorerFromJson(body: unknown): SchemaExplorerDto {
  if (!isRecord(body)) throw new Error('schema explorer must be an object');
  const focus = body.focus === undefined ? undefined : focusFromJson(body.focus);
  return {
    databaseName: requiredString(body, 'databaseName'),
    tableCount: requiredNumber(body, 'tableCount'),
    tables: requiredArray(body, 'tables').map(summaryFromJson),
    ...(focus === undefined ? {} : { focus }),
    reasoning: requiredString(body, 'reasoning'),
  };
}
