import type {
  AgreementRow,
  DepGroup,
  DepsManifestPanel,
  DirectDepRow,
  GroupRow,
  LockCounts,
  TransitiveRow,
  TransitiveSlice,
} from '../../domain/demo/dep-manifest';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
  requiredText,
} from '../content/validate';

/**
 * DepsManifestDTO — the wire/transport shape of the deps manifest panel.
 * Like every DTO constructor here it whitelists keys and throws on shape
 * violations, so hostile or drifted payloads surface loudly instead of
 * reaching the domain half-parsed. The nullable sub-panels (slice,
 * counts, agreement) are null exactly when the server degraded to
 * `available: false`; `satisfies` is boolean-or-null because the server
 * honestly refuses to judge operators it does not understand.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function depGroup(value: unknown): DepGroup {
  if (value !== 'main' && value !== 'dev') {
    throw new Error(`unknown dependency group: ${String(value)}`);
  }
  return value;
}

function groupRowFromJson(value: unknown): GroupRow {
  if (!isRecord(value)) throw new Error('group row must be an object');
  return {
    group: depGroup(value['group']),
    title: requiredString(value, 'title'),
    declaredIn: requiredString(value, 'declaredIn'),
    directCount: requiredNumber(value, 'directCount'),
    note: requiredString(value, 'note'),
  };
}

function directRowFromJson(value: unknown): DirectDepRow {
  if (!isRecord(value)) throw new Error('direct dep row must be an object');
  const satisfies = value['satisfies'];
  if (satisfies !== null && typeof satisfies !== 'boolean') {
    throw new Error(`expected boolean or null: satisfies (${String(satisfies)})`);
  }
  // An empty extras string is DATA (no extras requested), not absence.
  return {
    name: requiredString(value, 'name'),
    group: depGroup(value['group']),
    constraint: requiredText(value, 'constraint'),
    lockedVersion: requiredString(value, 'lockedVersion'),
    satisfies,
    extras: requiredText(value, 'extras'),
  };
}

function transitiveRowFromJson(value: unknown): TransitiveRow {
  if (!isRecord(value)) throw new Error('transitive row must be an object');
  return {
    name: requiredString(value, 'name'),
    lockedVersion: requiredString(value, 'lockedVersion'),
  };
}

function sliceFromJson(value: unknown): TransitiveSlice {
  if (!isRecord(value)) throw new Error('tree slice must be an object');
  return {
    root: requiredString(value, 'root'),
    rootConstraint: requiredText(value, 'rootConstraint'),
    rootLockedVersion: requiredString(value, 'rootLockedVersion'),
    children: requiredArray(value, 'children').map(transitiveRowFromJson),
    note: requiredString(value, 'note'),
  };
}

function countsFromJson(value: unknown): LockCounts {
  if (!isRecord(value)) throw new Error('lock counts must be an object');
  return {
    totalLocked: requiredNumber(value, 'totalLocked'),
    direct: requiredNumber(value, 'direct'),
    transitive: requiredNumber(value, 'transitive'),
    note: requiredString(value, 'note'),
  };
}

function agreementFromJson(value: unknown): AgreementRow {
  if (!isRecord(value)) throw new Error('agreement row must be an object');
  return {
    manifestNames: requiredNumber(value, 'manifestNames'),
    lockNames: requiredNumber(value, 'lockNames'),
    missingFromLock: requiredArray(value, 'missingFromLock').map((name) => {
      if (typeof name !== 'string') throw new Error('missing-from-lock name must be a string');
      return name;
    }),
    extraInLock: requiredArray(value, 'extraInLock').map((name) => {
      if (typeof name !== 'string') throw new Error('extra-in-lock name must be a string');
      return name;
    }),
    agree: requiredBoolean(value, 'agree'),
  };
}

/** Deserialize + validate the manifest panel (degradation included). */
export function depsManifestPanelFromJson(body: unknown): DepsManifestPanel {
  if (!isRecord(body)) throw new Error('deps manifest panel must be an object');
  return {
    manifestFile: requiredString(body, 'manifestFile'),
    lockFile: requiredString(body, 'lockFile'),
    available: requiredBoolean(body, 'available'),
    unavailableReason: stringOrNull(body, 'unavailableReason'),
    requiresPython: stringOrNull(body, 'requiresPython'),
    groups: requiredArray(body, 'groups').map(groupRowFromJson),
    direct: requiredArray(body, 'direct').map(directRowFromJson),
    slice: sliceOrNull(body, 'slice'),
    counts: countsOrNull(body, 'counts'),
    agreement: agreementOrNull(body, 'agreement'),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}

function sliceOrNull(source: Record<string, unknown>, key: string): TransitiveSlice | null {
  const value = source[key];
  if (value === null || value === undefined) return null;
  return sliceFromJson(value);
}

function countsOrNull(source: Record<string, unknown>, key: string): LockCounts | null {
  const value = source[key];
  if (value === null || value === undefined) return null;
  return countsFromJson(value);
}

function agreementOrNull(source: Record<string, unknown>, key: string): AgreementRow | null {
  const value = source[key];
  if (value === null || value === undefined) return null;
  return agreementFromJson(value);
}
