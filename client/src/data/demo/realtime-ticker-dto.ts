import type {
  TickerEndpointRow,
  TickerPanel,
  TickerPolicy,
  TickerStats,
  TickerTick,
} from '../../domain/demo/realtime-ticker';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * RealtimeTickerDTO — the wire/transport shapes of the ticker demo's two
 * JSON endpoints (panel, stats) plus the tick payload the EventSource
 * dispatches, validated field-by-field so a shape violation surfaces as a
 * typed invalid_response failure instead of "[object Object]" reaching
 * the UI. `oldestSeq`/`newestSeq` are the only nulls on the wire (an
 * empty ring has no bounds).
 */

function statsFromJson(value: unknown): TickerStats {
  if (!isRecord(value)) throw new Error('ticker stats must be an object');
  const oldest = value['oldestSeq'];
  const newest = value['newestSeq'];
  if (oldest !== null && typeof oldest !== 'number') {
    throw new Error('oldestSeq must be a number or null');
  }
  if (newest !== null && typeof newest !== 'number') {
    throw new Error('newestSeq must be a number or null');
  }
  return {
    ticksSent: requiredNumber(value, 'ticksSent'),
    clientsServed: requiredNumber(value, 'clientsServed'),
    resumeReplays: requiredNumber(value, 'resumeReplays'),
    ringRetained: requiredNumber(value, 'ringRetained'),
    oldestSeq: oldest,
    newestSeq: newest,
  };
}

function endpointFromJson(value: unknown): TickerEndpointRow {
  if (!isRecord(value)) throw new Error('ticker endpoint row must be an object');
  return {
    path: requiredString(value, 'path'),
    method: requiredString(value, 'method'),
    teaches: requiredString(value, 'teaches'),
  };
}

/** Deserialize + validate the ticker panel. */
export function tickerPanelFromJson(body: unknown): TickerPanel {
  if (!isRecord(body)) throw new Error('ticker panel must be an object');
  const policy = body['policy'];
  if (!isRecord(policy)) throw new Error('policy must be an object');
  const parsedPolicy: TickerPolicy = {
    symbols: requiredArray(policy, 'symbols').map((symbol) => {
      if (typeof symbol !== 'string') throw new Error('symbols must be strings');
      return symbol;
    }),
    defaultPaceMs: requiredNumber(policy, 'defaultPaceMs'),
    retryMs: requiredNumber(policy, 'retryMs'),
    keepaliveEvery: requiredNumber(policy, 'keepaliveEvery'),
    ringCapacity: requiredNumber(policy, 'ringCapacity'),
    mediaType: requiredString(policy, 'mediaType'),
  };
  const honestyNotes = requiredArray(body, 'honestyNotes').map((note) => {
    if (typeof note !== 'string') throw new Error('honesty notes must be strings');
    return note;
  });
  return {
    policy: parsedPolicy,
    stats: statsFromJson(body['stats']),
    endpoints: requiredArray(body, 'endpoints').map(endpointFromJson),
    honestyNotes,
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the firehose stats. */
export function tickerStatsFromJson(body: unknown): TickerStats {
  if (!isRecord(body)) throw new Error('ticker stats payload must be an object');
  return statsFromJson(body['stats']);
}

/** Parse one `data:` payload dispatched by the EventSource. */
export function tickerTickFromJson(body: unknown): TickerTick {
  if (!isRecord(body)) throw new Error('tick payload must be an object');
  return {
    seq: requiredNumber(body, 'seq'),
    symbol: requiredString(body, 'symbol'),
    price: requiredNumber(body, 'price'),
    change: requiredNumber(body, 'change'),
    at: requiredNumber(body, 'at'),
  };
}
