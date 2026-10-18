import {
  type ConsoleOperationRow,
  type ExplainStageRow,
  type IndexShowcaseRow,
  type MongoConsoleDemo,
  type RefusalRow,
  type SeedReport,
  type TtlShowcaseRow,
} from '../../domain/demo/mongo-console';
import {
  isRecord,
  optionalString,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * MongoConsoleDTO — the wire/transport shapes of the mongo console:
 * seed, refusal, the operation lifecycle, and the two exhibits
 * (index explain + TTL definition).
 */

export type MongoConsoleDto = MongoConsoleDemo;

/** A Record<string, string> row (document display strings). */
function documentFromJson(value: unknown): Record<string, string> {
  if (!isRecord(value)) throw new Error('document row must be an object');
  const row: Record<string, string> = {};
  for (const [field, cell] of Object.entries(value)) {
    if (typeof cell !== 'string') {
      throw new Error(`expected string cell at "${field}"`);
    }
    row[field] = cell;
  }
  return row;
}

function documentsFromJson(value: Record<string, unknown>): Record<string, string>[] {
  return requiredArray(value, 'documents').map(documentFromJson);
}

function stringRecordFromJson(value: unknown, label: string): Record<string, string> {
  if (!isRecord(value)) throw new Error(`${label} must be an object`);
  const record: Record<string, string> = {};
  for (const [field, cell] of Object.entries(value)) {
    if (typeof cell !== 'string') {
      throw new Error(`expected string at "${label}.${field}"`);
    }
    record[field] = cell;
  }
  return record;
}

function seedFromJson(body: Record<string, unknown>): SeedReport {
  const seed = requiredRecord(body, 'seed');
  return {
    collection: requiredString(seed, 'collection'),
    seedKeys: requiredArray(seed, 'seedKeys').map((key) => {
      if (typeof key !== 'string') throw new Error('expected seed key string');
      return key;
    }),
    countBefore: requiredNumber(seed, 'countBefore'),
    upserted: requiredNumber(seed, 'upserted'),
    totalAfter: requiredNumber(seed, 'totalAfter'),
    indexesEnsured: requiredArray(seed, 'indexesEnsured').map((name) => {
      if (typeof name !== 'string') throw new Error('expected index name string');
      return name;
    }),
  };
}

function refusalFromJson(body: Record<string, unknown>): RefusalRow {
  const refusal = requiredRecord(body, 'refusal');
  return {
    attempted: stringRecordFromJson(refusal.attempted, 'attempted'),
    errors: requiredArray(refusal, 'errors').map((line) => {
      if (typeof line !== 'string') throw new Error('expected refusal error string');
      return line;
    }),
  };
}

function operationFromJson(value: unknown): ConsoleOperationRow {
  if (!isRecord(value)) throw new Error('operation row must be an object');
  return {
    op: requiredString(value, 'op'),
    description: requiredString(value, 'description'),
    command: requiredString(value, 'command'),
    outcome: requiredString(value, 'outcome'),
    documents: documentsFromJson(value),
  };
}

function explainFromJson(value: unknown): ExplainStageRow {
  if (!isRecord(value)) throw new Error('explain stage must be an object');
  return {
    label: requiredString(value, 'label'),
    query: requiredString(value, 'query'),
    stage: requiredString(value, 'stage'),
    indexName: optionalString(value, 'indexName'),
    keysExamined: requiredNumber(value, 'keysExamined'),
    docsExamined: requiredNumber(value, 'docsExamined'),
  };
}

function indexShowcaseFromJson(body: Record<string, unknown>): IndexShowcaseRow {
  const showcase = requiredRecord(body, 'indexShowcase');
  return {
    collection: requiredString(showcase, 'collection'),
    documentCount: requiredNumber(showcase, 'documentCount'),
    indexCommand: requiredString(showcase, 'indexCommand'),
    explains: requiredArray(showcase, 'explains').map(explainFromJson),
  };
}

function ttlShowcaseFromJson(body: Record<string, unknown>): TtlShowcaseRow {
  const showcase = requiredRecord(body, 'ttlShowcase');
  return {
    collection: requiredString(showcase, 'collection'),
    indexDefinition: stringRecordFromJson(showcase.indexDefinition, 'indexDefinition'),
    expireAfterSeconds: requiredNumber(showcase, 'expireAfterSeconds'),
    scratchDocuments: requiredArray(showcase, 'scratchDocuments').map(documentFromJson),
    evictionNote: requiredString(showcase, 'evictionNote'),
  };
}

/** Deserialize + validate the mongo console payload (console + exhibits). */
export function mongoConsoleFromJson(body: unknown): MongoConsoleDto {
  if (!isRecord(body)) throw new Error('mongo console demo must be an object');
  return {
    database: requiredString(body, 'database'),
    seed: seedFromJson(body),
    refusal: refusalFromJson(body),
    operations: requiredArray(body, 'operations').map(operationFromJson),
    indexShowcase: indexShowcaseFromJson(body),
    ttlShowcase: ttlShowcaseFromJson(body),
    reasoning: requiredString(body, 'reasoning'),
  };
}
