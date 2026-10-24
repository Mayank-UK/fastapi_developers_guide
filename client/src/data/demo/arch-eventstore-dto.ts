import type {
  AppendedEventRow,
  ArchEventStorePanel,
  ConcurrencyRow,
  ContrastRow,
  FoldStepRow,
  KinshipRow,
  RebuildRow,
  StoreFactsRow,
} from '../../domain/demo/arch-eventstore';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * ArchEventStoreDTO — the wire/transport shape of the event-store
 * panel. Every field is always present on this payload; validation
 * happens at the boundary so a drifted wire fails HERE, not in a view.
 */

function storeFactsFromJson(value: unknown): StoreFactsRow {
  if (!isRecord(value)) throw new Error('store facts must be an object');
  return {
    port: requiredString(value, 'port'),
    adapter: requiredString(value, 'adapter'),
    stream: requiredString(value, 'stream'),
    events: requiredNumber(value, 'events'),
  };
}

function appendedFromJson(value: unknown): AppendedEventRow {
  if (!isRecord(value)) throw new Error('appended event row must be an object');
  return {
    version: requiredNumber(value, 'version'),
    eventType: requiredString(value, 'eventType'),
    payload: requiredString(value, 'payload'),
    eventId: requiredString(value, 'eventId'),
    occurredAt: requiredString(value, 'occurredAt'),
  };
}

function foldStepFromJson(value: unknown): FoldStepRow {
  if (!isRecord(value)) throw new Error('fold step row must be an object');
  return {
    afterVersion: requiredNumber(value, 'afterVersion'),
    eventType: requiredString(value, 'eventType'),
    stateNow: requiredString(value, 'stateNow'),
  };
}

function rebuildFromJson(value: unknown): RebuildRow {
  if (!isRecord(value)) throw new Error('rebuild row must be an object');
  return {
    method: requiredString(value, 'method'),
    state: requiredRecord(value, 'state'),
    matches: requiredBoolean(value, 'matches'),
    evidence: requiredString(value, 'evidence'),
  };
}

function concurrencyFromJson(value: unknown): ConcurrencyRow {
  if (!isRecord(value)) throw new Error('concurrency row must be an object');
  return {
    writer: requiredString(value, 'writer'),
    expectedVersion: requiredNumber(value, 'expectedVersion'),
    actualVersion: requiredNumber(value, 'actualVersion'),
    storedEventsAfter: requiredNumber(value, 'storedEventsAfter'),
    evidence: requiredString(value, 'evidence'),
  };
}

function contrastFromJson(value: unknown): ContrastRow {
  if (!isRecord(value)) throw new Error('contrast row must be an object');
  return {
    approach: requiredString(value, 'approach'),
    keeps: requiredString(value, 'keeps'),
    history: requiredString(value, 'history'),
    answers: requiredString(value, 'answers'),
  };
}

function kinshipFromJson(value: unknown): KinshipRow {
  if (!isRecord(value)) throw new Error('kinship row must be an object');
  return {
    relative: requiredString(value, 'relative'),
    where: requiredString(value, 'where'),
    same: requiredString(value, 'same'),
    different: requiredString(value, 'different'),
  };
}

/** Deserialize + validate the event-store panel (store..kinship, note). */
export function archEventStorePanelFromJson(body: unknown): ArchEventStorePanel {
  if (!isRecord(body)) throw new Error('arch eventstore panel must be an object');
  return {
    store: storeFactsFromJson(body['store']),
    appended: requiredArray(body, 'appended').map(appendedFromJson),
    foldSteps: requiredArray(body, 'foldSteps').map(foldStepFromJson),
    currentState: requiredRecord(body, 'currentState'),
    rebuild: rebuildFromJson(body['rebuild']),
    concurrency: concurrencyFromJson(body['concurrency']),
    contrast: requiredArray(body, 'contrast').map(contrastFromJson),
    kinship: kinshipFromJson(body['kinship']),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
