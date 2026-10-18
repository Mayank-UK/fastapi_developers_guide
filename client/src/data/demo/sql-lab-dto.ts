import { type ExhibitCard, type SqlLab } from '../../domain/demo/sql-lab';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * SqlLabDTO — the wire/transport shapes of the SQL lab. Rows are
 * display-formatted string maps keyed by column name; every value must
 * be a string (the server formats dates and numerals as text).
 */

export type SqlLabDto = SqlLab;

function exhibitFromJson(body: unknown): ExhibitCard {
  if (!isRecord(body)) throw new Error('exhibit card must be an object');
  return {
    id: requiredString(body, 'id'),
    name: requiredString(body, 'name'),
    teaches: requiredString(body, 'teaches'),
  };
}

function rowCell(value: unknown, column: string): string {
  if (typeof value !== 'string') {
    throw new Error(`expected string cell at column "${column}"`);
  }
  return value;
}

function rowFromJson(body: unknown): Record<string, string> {
  if (!isRecord(body)) throw new Error('lab row must be an object');
  const row: Record<string, string> = {};
  for (const [column, value] of Object.entries(body)) {
    row[column] = rowCell(value, column);
  }
  return row;
}

/** Deserialize + validate one exhibit's answer. */
export function sqlLabFromJson(body: unknown): SqlLabDto {
  if (!isRecord(body)) throw new Error('sql lab must be an object');
  return {
    exhibit: requiredString(body, 'exhibit'),
    exhibits: requiredArray(body, 'exhibits').map(exhibitFromJson),
    sql: requiredString(body, 'sql'),
    columns: requiredArray(body, 'columns').map((column) => rowCell(column, 'columns')),
    rows: requiredArray(body, 'rows').map(rowFromJson),
    rowCount: requiredNumber(body, 'rowCount'),
    reading: requiredString(body, 'reading'),
    reasoning: requiredString(body, 'reasoning'),
  };
}
