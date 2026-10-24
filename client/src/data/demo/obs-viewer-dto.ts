import type { CapturedEvent, EventField, LogViewerPanel, PipelineStage } from '../../domain/demo/obs-viewer';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
  requiredText,
} from '../content/validate';

/**
 * ObsViewerDTO — the wire/transport shape of the structured-log viewer.
 * Like every DTO constructor here it whitelists keys and throws on shape
 * violations, so hostile or drifted payloads surface loudly instead of
 * reaching the domain half-parsed. The captured-event parser is exported
 * because the trace fan-out's log rows are the same wire shape.
 *
 * Empty strings are DATA in several event fields, per the server's own
 * contract: `requestId` is empty for events logged outside any request
 * (startup warnings, background work), and `event`/`timestamp` may be
 * empty when the pipeline never stamped them — those use requiredText
 * (present-but-empty passes); the fields that are always populated use
 * requiredString.
 */

export function capturedEventFromJson(value: unknown): CapturedEvent {
  if (!isRecord(value)) throw new Error('captured event must be an object');
  return {
    sequence: requiredNumber(value, 'sequence'),
    level: requiredString(value, 'level'),
    event: requiredText(value, 'event'),
    requestId: requiredText(value, 'requestId'),
    timestamp: requiredText(value, 'timestamp'),
    fields: requiredArray(value, 'fields').map(eventFieldFromJson),
  };
}

function eventFieldFromJson(value: unknown): EventField {
  if (!isRecord(value)) throw new Error('event field must be an object');
  return {
    name: requiredString(value, 'name'),
    value: requiredText(value, 'value'),
  };
}

function pipelineStageFromJson(value: unknown): PipelineStage {
  if (!isRecord(value)) throw new Error('pipeline stage must be an object');
  return {
    orderIndex: requiredNumber(value, 'orderIndex'),
    processor: requiredString(value, 'processor'),
    role: requiredString(value, 'role'),
  };
}

/** Deserialize + validate the viewer panel (pipeline, level, real events). */
export function logViewerPanelFromJson(body: unknown): LogViewerPanel {
  if (!isRecord(body)) throw new Error('log viewer panel must be an object');
  return {
    configuredLevel: requiredString(body, 'configuredLevel'),
    levelSource: requiredString(body, 'levelSource'),
    ringCapacity: requiredNumber(body, 'ringCapacity'),
    pipeline: requiredArray(body, 'pipeline').map(pipelineStageFromJson),
    events: requiredArray(body, 'events').map(capturedEventFromJson),
    panelRequestId: requiredString(body, 'panelRequestId'),
    pipelineNote: requiredString(body, 'pipelineNote'),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
