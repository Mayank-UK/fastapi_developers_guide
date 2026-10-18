import type {
  ErrorKindRow,
  ErrorsPanel,
  ProbeOutcome,
  ScenarioSnapshot,
  TriggerMode,
  TriggerSpec,
} from '../../domain/demo/errors-explorer';
import { isRecord, requiredArray, requiredNumber, requiredString } from '../content/validate';

/**
 * ErrorsExplorerDTO — the wire/transport shapes of the explorer: the panel
 * (eight kind rows from the taxonomy's own tables) and the two scenario
 * endpoints' answers. The observed-failure halves are built by the API from
 * raw rounds (a failure's status/envelope/headers are the payload, and the
 * shared JSON pipeline structurally cannot represent a non-2xx body).
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function triggerFromJson(value: unknown): TriggerSpec {
  if (!isRecord(value)) throw new Error('trigger must be an object');
  const mode = requiredString(value, 'mode');
  if (mode !== 'live' && mode !== 'recipe') throw new Error(`unknown trigger mode: ${mode}`);
  return {
    mode: mode as TriggerMode,
    method: requiredString(value, 'method'),
    path: requiredString(value, 'path'),
    body: stringOrNull(value, 'body'),
    prep: stringOrNull(value, 'prep'),
    note: requiredString(value, 'note'),
  };
}

function kindRowFromJson(value: unknown): ErrorKindRow {
  if (!isRecord(value)) throw new Error('kind row must be an object');
  return {
    kind: requiredString(value, 'kind'),
    httpStatus: requiredNumber(value, 'httpStatus'),
    defaultMessage: requiredString(value, 'defaultMessage'),
    raisedBy: requiredString(value, 'raisedBy'),
    loggedAs: requiredString(value, 'loggedAs'),
    trigger: triggerFromJson(value['trigger']),
  };
}

function scenarioMode(value: unknown, label: string): ScenarioSnapshot['injectFailure'] {
  if (value !== 'none' && value !== 'error' && value !== 'latency') {
    throw new Error(`unknown ${label}: ${String(value)}`);
  }
  return value;
}

/** Deserialize + validate the explorer panel. */
export function errorsPanelFromJson(body: unknown): ErrorsPanel {
  if (!isRecord(body)) throw new Error('errors panel must be an object');
  const scenario = body['scenario'];
  const probe = body['probe'];
  if (!isRecord(scenario)) throw new Error('scenario must be an object');
  if (!isRecord(probe)) throw new Error('probe must be an object');
  return {
    kinds: requiredArray(body, 'kinds').map(kindRowFromJson),
    envelopeNote: requiredString(body, 'envelopeNote'),
    scenario: {
      getEndpoint: requiredString(scenario, 'getEndpoint'),
      patchEndpoint: requiredString(scenario, 'patchEndpoint'),
      modes: requiredArray(scenario, 'modes').map((mode) => {
        if (typeof mode !== 'string') throw new Error('mode must be a string');
        return scenarioMode(mode, 'scenario mode');
      }),
      note: requiredString(scenario, 'note'),
    },
    probe: {
      probeEndpoint: requiredString(probe, 'probeEndpoint'),
      latencySeconds: requiredNumber(probe, 'latencySeconds'),
      healthyNote: requiredString(probe, 'healthyNote'),
      injectedNote: requiredString(probe, 'injectedNote'),
      latencyNote: requiredString(probe, 'latencyNote'),
    },
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the scenario store's snapshot. */
export function scenarioSnapshotFromJson(body: unknown): ScenarioSnapshot {
  if (!isRecord(body)) throw new Error('scenario snapshot must be an object');
  const dataMode = requiredString(body, 'dataMode');
  if (dataMode !== 'fake' && dataMode !== 'live') {
    throw new Error(`unknown data mode: ${dataMode}`);
  }
  return {
    dataMode,
    injectFailure: scenarioMode(body['injectFailure'], 'injectFailure'),
  };
}

/** Deserialize + validate the probe's healthy row. */
export function probeOutcomeFromJson(body: unknown): ProbeOutcome {
  if (!isRecord(body)) throw new Error('probe outcome must be an object');
  return {
    status: requiredString(body, 'status'),
    injectFailure: requiredString(body, 'injectFailure'),
    detail: requiredString(body, 'detail'),
  };
}
