import type { StallAllocations, StallPanel, StallPhase } from '../../domain/demo/debug-stall';
import { capturedEventFromJson } from './obs-viewer-dto';
import { isRecord, requiredArray, requiredNumber, requiredString } from '../content/validate';

/**
 * DebugStallDTO — the wire/transport shape of the stall diagnosis. Every
 * field is always present on this payload (no nullables): each phase
 * carries all instruments, the log rows reuse the viewer's captured-event
 * parser — the same wire shape on both panels.
 */

function stallPhaseFromJson(value: unknown): StallPhase {
  if (!isRecord(value)) throw new Error('stall phase must be an object');
  return {
    label: requiredString(value, 'label'),
    what: requiredString(value, 'what'),
    elapsedMs: requiredNumber(value, 'elapsedMs'),
    loopLagMaxMs: requiredNumber(value, 'loopLagMaxMs'),
    loopLagMeanMs: requiredNumber(value, 'loopLagMeanMs'),
    concurrentHealthMs: requiredNumber(value, 'concurrentHealthMs'),
    concurrentHealthStatus: requiredNumber(value, 'concurrentHealthStatus'),
    verdict: requiredString(value, 'verdict'),
  };
}

function stallAllocationsFromJson(value: unknown): StallAllocations {
  if (!isRecord(value)) throw new Error('stall allocations must be an object');
  return {
    workload: requiredString(value, 'workload'),
    objects: requiredNumber(value, 'objects'),
    currentKb: requiredNumber(value, 'currentKb'),
    peakKb: requiredNumber(value, 'peakKb'),
    note: requiredString(value, 'note'),
  };
}

/** Deserialize + validate the stall panel (phases, allocations, log rows). */
export function stallPanelFromJson(body: unknown): StallPanel {
  if (!isRecord(body)) throw new Error('stall panel must be an object');
  return {
    panelRequestId: requiredString(body, 'panelRequestId'),
    phases: requiredArray(body, 'phases').map(stallPhaseFromJson),
    allocations: stallAllocationsFromJson(body['allocations']),
    logEvents: requiredArray(body, 'logEvents').map(capturedEventFromJson),
    pySpyNote: requiredString(body, 'pySpyNote'),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
