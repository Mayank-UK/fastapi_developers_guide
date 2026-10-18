import {
  type MigrationRun,
  type MigrationStep,
  type MigrationsDemo,
} from '../../domain/demo/db-migrations';
import {
  isRecord,
  optionalNumber,
  optionalString,
  requiredArray,
  requiredBoolean,
  requiredString,
} from '../content/validate';

/**
 * DbMigrationsDTO — the wire/transport shapes of the migration
 * rehearsal. Mirrors the domain models 1:1; `failure` and
 * `rowCountAfter` are optional wire fields (absent = committed run /
 * no table), surfaced as undefined, never null.
 */

export type DbMigrationsDto = MigrationsDemo;

function stepFromJson(body: unknown): MigrationStep {
  if (!isRecord(body)) throw new Error('migration step must be an object');
  return {
    description: requiredString(body, 'description'),
    sql: requiredString(body, 'sql'),
    outcome: requiredString(body, 'outcome'),
  };
}

function runFromJson(body: unknown): MigrationRun {
  if (!isRecord(body)) throw new Error('migration run must be an object');
  const failure = optionalString(body, 'failure');
  const rowCountAfter = optionalNumber(body, 'rowCountAfter');
  return {
    scenario: requiredString(body, 'scenario'),
    scratchTable: requiredString(body, 'scratchTable'),
    steps: requiredArray(body, 'steps').map(stepFromJson),
    ...(failure === undefined ? {} : { failure }),
    committed: requiredBoolean(body, 'committed'),
    tableExistsAfter: requiredBoolean(body, 'tableExistsAfter'),
    ...(rowCountAfter === undefined ? {} : { rowCountAfter }),
  };
}

/** Deserialize + validate the rehearsal payload (both runs). */
export function dbMigrationsFromJson(body: unknown): DbMigrationsDto {
  if (!isRecord(body)) throw new Error('migrations demo must be an object');
  return {
    scratchTable: requiredString(body, 'scratchTable'),
    failing: runFromJson(body.failing),
    succeeding: runFromJson(body.succeeding),
    cleanupNote: requiredString(body, 'cleanupNote'),
    reasoning: requiredString(body, 'reasoning'),
  };
}
