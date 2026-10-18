import type {
  ConfigFactsRow,
  DataMode,
  EnvInspectorPanel,
  FailureInjection,
  FlagsPanelRow,
  ScenarioSnapshot,
  SettingRow,
  SettingSource,
} from '../../domain/demo/env-inspector';
import { isRecord, requiredArray, requiredBoolean, requiredRecord, requiredString, requiredText } from '../content/validate';

/**
 * EnvInspectorDTO — the wire/transport shapes of the env inspector: the
 * panel (one row per config field, with honest source attribution and
 * server-side redaction) and the scenario store's PATCH answers. Like
 * every DTO constructor here it whitelists keys and throws on shape
 * violations, so hostile or drifted payloads surface loudly instead of
 * reaching the domain half-parsed.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function settingSource(value: unknown): SettingSource {
  if (value !== 'env' && value !== 'default') {
    throw new Error(`unknown setting source: ${String(value)}`);
  }
  return value;
}

function dataMode(value: unknown): DataMode {
  if (value !== 'fake' && value !== 'live') {
    throw new Error(`unknown data mode: ${String(value)}`);
  }
  return value;
}

function failureInjection(value: unknown): FailureInjection {
  if (value !== 'none' && value !== 'error' && value !== 'latency') {
    throw new Error(`unknown failure injection: ${String(value)}`);
  }
  return value;
}

function settingRowFromJson(value: unknown): SettingRow {
  if (!isRecord(value)) throw new Error('setting row must be an object');
  return {
    name: requiredString(value, 'name'),
    envVar: requiredString(value, 'envVar'),
    type: requiredString(value, 'type'),
    // An empty value is DATA (an env var deliberately set to ""), not absence.
    value: requiredText(value, 'value'),
    source: settingSource(value['source']),
    secret: requiredBoolean(value, 'secret'),
    redacted: requiredBoolean(value, 'redacted'),
    shapeHint: stringOrNull(value, 'shapeHint'),
  };
}

function factsFromJson(value: unknown): ConfigFactsRow {
  if (!isRecord(value)) throw new Error('config facts must be an object');
  return {
    envPrefix: requiredString(value, 'envPrefix'),
    frozen: requiredBoolean(value, 'frozen'),
    cache: requiredString(value, 'cache'),
  };
}

function flagsFromJson(value: unknown): FlagsPanelRow {
  if (!isRecord(value)) throw new Error('flags panel must be an object');
  return {
    getEndpoint: requiredString(value, 'getEndpoint'),
    patchEndpoint: requiredString(value, 'patchEndpoint'),
    dataMode: dataMode(value['dataMode']),
    injectFailure: failureInjection(value['injectFailure']),
    note: requiredString(value, 'note'),
  };
}

/** Deserialize + validate the inspector panel. */
export function envInspectorPanelFromJson(body: unknown): EnvInspectorPanel {
  if (!isRecord(body)) throw new Error('env inspector panel must be an object');
  return {
    environment: requiredText(body, 'environment'),
    envVar: requiredString(body, 'envVar'),
    facts: factsFromJson(requiredRecord(body, 'facts')),
    settings: requiredArray(body, 'settings').map(settingRowFromJson),
    sourceNote: requiredString(body, 'sourceNote'),
    redactionNote: requiredString(body, 'redactionNote'),
    flags: flagsFromJson(requiredRecord(body, 'flags')),
  };
}

/** Deserialize + validate the scenario store's snapshot. */
export function scenarioSnapshotFromJson(body: unknown): ScenarioSnapshot {
  if (!isRecord(body)) throw new Error('scenario snapshot must be an object');
  return {
    dataMode: dataMode(body['dataMode']),
    injectFailure: failureInjection(body['injectFailure']),
  };
}
