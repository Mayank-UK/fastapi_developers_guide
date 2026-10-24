import type { TraceFanout, TraceRound } from '../../domain/demo/obs-trace';
import { capturedEventFromJson } from './obs-viewer-dto';
import { isRecord, requiredArray, requiredBoolean, requiredNumber, requiredString } from '../content/validate';

/**
 * ObsTraceDTO — the wire/transport shape of the trace fan-out. The
 * nullable envelope fields are null exactly on the healthy round (2xx
 * responses carry no error envelope to correlate); the log rows reuse the
 * viewer's captured-event parser — the same wire shape on both panels.
 */

function stringOrNull(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  if (value === null) return null;
  if (typeof value !== 'string') throw new Error(`expected string or null: ${key}`);
  return value;
}

function traceRoundFromJson(value: unknown): TraceRound {
  if (!isRecord(value)) throw new Error('trace round must be an object');
  return {
    label: requiredString(value, 'label'),
    requestLine: requiredString(value, 'requestLine'),
    inboundRequestId: requiredString(value, 'inboundRequestId'),
    status: requiredNumber(value, 'status'),
    firstByteMs: requiredNumber(value, 'firstByteMs'),
    durationMs: requiredNumber(value, 'durationMs'),
    headerEchoed: requiredBoolean(value, 'headerEchoed'),
    envelopeCode: stringOrNull(value, 'envelopeCode'),
    envelopeRequestId: stringOrNull(value, 'envelopeRequestId'),
    logEvents: requiredArray(value, 'logEvents').map(capturedEventFromJson),
    note: requiredString(value, 'note'),
  };
}

/** Deserialize + validate the trace fan-out (root, rounds, correlation). */
export function traceFanoutFromJson(body: unknown): TraceFanout {
  if (!isRecord(body)) throw new Error('trace fanout must be an object');
  return {
    rootRequestId: requiredString(body, 'rootRequestId'),
    derivedIdConvention: requiredString(body, 'derivedIdConvention'),
    rounds: requiredArray(body, 'rounds').map(traceRoundFromJson),
    correlationNote: requiredString(body, 'correlationNote'),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
