import type {
  DecisionRow,
  IntegrationRow,
  QuotaRow,
  SecretRow,
  ThirdPartyHubPanel,
} from '../../domain/demo/thirdparty-hub';
import { isRecord, requiredArray, requiredString } from '../content/validate';

/**
 * ThirdPartyHubDTO — the wire/transport shape of the third-party hub
 * panel. Every field is always present on this payload; validation
 * happens at the boundary so a drifted wire fails HERE, not in a view.
 */

function decisionRowFromJson(value: unknown): DecisionRow {
  if (!isRecord(value)) throw new Error('decision row must be an object');
  const choice = requiredString(value, 'choice');
  if (choice !== 'integrate' && choice !== 'build') {
    throw new Error(`decision row choice must be integrate|build, got ${choice}`);
  }
  return {
    id: requiredString(value, 'id'),
    choice,
    subject: requiredString(value, 'subject'),
    package: requiredString(value, 'package'),
    reason: requiredString(value, 'reason'),
    blastRadius: requiredString(value, 'blastRadius'),
    verified: requiredString(value, 'verified'),
  };
}

function integrationRowFromJson(value: unknown): IntegrationRow {
  if (!isRecord(value)) throw new Error('integration row must be an object');
  return {
    id: requiredString(value, 'id'),
    kind: requiredString(value, 'kind'),
    name: requiredString(value, 'name'),
    detail: requiredString(value, 'detail'),
    whenDown: requiredString(value, 'whenDown'),
    evidence: requiredString(value, 'evidence'),
  };
}

function secretRowFromJson(value: unknown): SecretRow {
  if (!isRecord(value)) throw new Error('secret row must be an object');
  return {
    id: requiredString(value, 'id'),
    envVar: requiredString(value, 'envVar'),
    scope: requiredString(value, 'scope'),
    blastRadius: requiredString(value, 'blastRadius'),
    handling: requiredString(value, 'handling'),
    evidence: requiredString(value, 'evidence'),
  };
}

function quotaRowFromJson(value: unknown): QuotaRow {
  if (!isRecord(value)) throw new Error('quota row must be an object');
  const source = requiredString(value, 'source');
  if (source !== 'live' && source !== 'constant') {
    throw new Error(`quota row source must be live|constant, got ${source}`);
  }
  return {
    id: requiredString(value, 'id'),
    quota: requiredString(value, 'quota'),
    scope: requiredString(value, 'scope'),
    atCeiling: requiredString(value, 'atCeiling'),
    source,
  };
}

/** Deserialize + validate the third-party hub (decisions..quotas, honesty note). */
export function thirdPartyHubPanelFromJson(body: unknown): ThirdPartyHubPanel {
  if (!isRecord(body)) throw new Error('third-party hub panel must be an object');
  return {
    decisions: requiredArray(body, 'decisions').map(decisionRowFromJson),
    integrations: requiredArray(body, 'integrations').map(integrationRowFromJson),
    secrets: requiredArray(body, 'secrets').map(secretRowFromJson),
    quotas: requiredArray(body, 'quotas').map(quotaRowFromJson),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
