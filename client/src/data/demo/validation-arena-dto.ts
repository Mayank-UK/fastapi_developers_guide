import {
  ARENA_MODEL_KEYS,
  type ArenaError,
  type ArenaFieldRow,
  type ArenaFieldSpec,
  type ArenaModelKey,
  type ArenaModelSummary,
  type ArenaOutcome,
  type ArenaRoster,
  type ArenaVerdict,
} from '../../domain/demo/validation-arena';
import {
  isRecord,
  optionalRecord,
  requiredArray,
  requiredBoolean,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * ValidationArenaDTO — the wire/transport shapes of the validation arena.
 * Mirrors the domain models 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builders construct ONLY the listed
 * fields (whitelist) and throw on any shape violation, which parseDto
 * upgrades to an InvalidResponseException. Optional wire fields (received,
 * validated, errors, an absent field's default) stay undefined when the
 * server omitted them — the null-as-invalid rule everywhere else in this
 * client.
 */

export type ArenaRosterDto = ArenaRoster;
export type ArenaVerdictDto = ArenaVerdict;

/** Deserialize + validate one roster field's rule row. */
export function arenaFieldSpecFromJson(body: unknown): ArenaFieldSpec {
  if (!isRecord(body)) throw new Error('field spec must be an object');
  return {
    name: requiredString(body, 'name'),
    rule: requiredString(body, 'rule'),
    required: requiredBoolean(body, 'required'),
  };
}

/** Deserialize + validate one roster model summary. */
export function arenaModelSummaryFromJson(body: unknown): ArenaModelSummary {
  if (!isRecord(body)) throw new Error('model summary must be an object');
  const key = requiredString(body, 'key');
  if (!ARENA_MODEL_KEYS.includes(key as ArenaModelKey)) {
    throw new Error(`unknown arena model key: ${key}`);
  }
  return {
    key: key as ArenaModelKey,
    model: requiredString(body, 'model'),
    source: requiredString(body, 'source'),
    description: requiredString(body, 'description'),
    fields: requiredArray(body, 'fields').map(arenaFieldSpecFromJson),
  };
}

/** Deserialize + validate the GET roster payload. */
export function arenaRosterFromJson(body: unknown): ArenaRosterDto {
  if (!isRecord(body)) throw new Error('arena roster must be an object');
  return {
    models: requiredArray(body, 'models').map(arenaModelSummaryFromJson),
    reasoning: requiredString(body, 'reasoning'),
  };
}

function stringList(source: Record<string, unknown>, key: string): string[] {
  return requiredArray(source, key).map((value) => nonEmptyString(value, key));
}

function nonEmptyString(value: unknown, key: string): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error(`expected a non-empty string in "${key}"`);
  }
  return value;
}

/** Deserialize + validate one field outcome, discriminated on `status`. */
export function arenaOutcomeFromJson(body: unknown): ArenaOutcome {
  if (!isRecord(body)) throw new Error('outcome must be an object');
  const status = requiredString(body, 'status');
  switch (status) {
    case 'accepted':
      return { status, value: body.value, valueType: requiredString(body, 'valueType') };
    case 'coerced':
      return {
        status,
        original: body.original,
        originalType: requiredString(body, 'originalType'),
        value: body.value,
        valueType: requiredString(body, 'valueType'),
      };
    case 'rejected':
      return {
        status,
        loc: stringList(body, 'loc'),
        msg: requiredString(body, 'msg'),
        type: requiredString(body, 'type'),
      };
    case 'absent':
      // `default` is omitted by the server when null; keep it raw otherwise.
      return 'default' in body ? { status, default: body.default } : { status };
    default:
      throw new Error(`unknown arena outcome status: ${status}`);
  }
}

/** Deserialize + validate one judged field row. */
export function arenaFieldRowFromJson(body: unknown): ArenaFieldRow {
  if (!isRecord(body)) throw new Error('field row must be an object');
  const received = optionalRecord(body, 'received');
  return {
    field: requiredString(body, 'field'),
    rule: requiredString(body, 'rule'),
    required: requiredBoolean(body, 'required'),
    ...(received === undefined ? {} : { received: receivedFromJson(received) }),
    outcome: arenaOutcomeFromJson(requiredRecord(body, 'outcome')),
  };
}

function receivedFromJson(body: Record<string, unknown>): ArenaFieldRow['received'] {
  return { type: requiredString(body, 'type'), repr: requiredString(body, 'repr') };
}

function arenaErrorFromJson(body: unknown): ArenaError {
  if (!isRecord(body)) throw new Error('arena error must be an object');
  return {
    loc: stringList(body, 'loc'),
    msg: requiredString(body, 'msg'),
    type: requiredString(body, 'type'),
  };
}

/** Deserialize + validate the POST verdict payload. */
export function arenaVerdictFromJson(body: unknown): ArenaVerdictDto {
  if (!isRecord(body)) throw new Error('arena verdict must be an object');
  const verdict = requiredString(body, 'verdict');
  if (verdict !== 'accepted' && verdict !== 'rejected') {
    throw new Error(`unknown arena verdict: ${verdict}`);
  }
  const validated = optionalRecord(body, 'validated');
  const errors = body.errors === undefined ? undefined : requiredArray(body, 'errors');
  return {
    model: arenaModelSummaryFromJson(requiredRecord(body, 'model')),
    roster: requiredArray(body, 'roster').map(arenaModelSummaryFromJson),
    rows: requiredArray(body, 'rows').map(arenaFieldRowFromJson),
    verdict,
    ...(validated === undefined ? {} : { validated }),
    ...(errors === undefined ? {} : { errors: errors.map(arenaErrorFromJson) }),
    extraKeysIgnored: stringList(body, 'extraKeysIgnored'),
    reasoning: requiredString(body, 'reasoning'),
  };
}
