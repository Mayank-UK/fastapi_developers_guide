import type {
  RuntimeStreamingDemoData,
  StreamChunk,
  StreamChunkKind,
} from '../../domain/demo/runtime-streaming';
import { isRecord, optionalString, requiredNumber, requiredString } from '../content/validate';

/**
 * RuntimeStreamingDTO — the wire/transport shape of the streaming demo.
 * Each NDJSON line is validated independently (whitelist + kind check) and
 * throws on any shape violation; the API layer upgrades a throw to an
 * InvalidResponseException naming the offending line.
 */

export type RuntimeStreamingDemoDto = RuntimeStreamingDemoData;

const CHUNK_KINDS: readonly StreamChunkKind[] = ['open', 'item', 'closed'];

/** Validate one NDJSON line into a chunk (throws on shape violation). */
export function streamChunkFromJson(body: unknown): StreamChunk {
  if (!isRecord(body)) throw new Error('stream chunk must be an object');
  const kind = requiredString(body, 'kind') as StreamChunkKind;
  if (!CHUNK_KINDS.includes(kind)) {
    throw new Error(`unknown stream chunk kind "${kind}"`);
  }
  return {
    seq: requiredNumber(body, 'seq'),
    kind,
    label: requiredString(body, 'label'),
    detail: optionalString(body, 'detail'),
    itemsDelivered: optionalNumber(body, 'itemsDelivered'),
    totalMs: optionalNumber(body, 'totalMs'),
  };
}

/** Parse one NDJSON text line (already newline-stripped) into a chunk. */
export function streamChunkFromLine(line: string): StreamChunk {
  let parsed: unknown;
  try {
    parsed = JSON.parse(line);
  } catch (error) {
    throw new Error(`stream line is not JSON: ${line.slice(0, 40)}`, { cause: error });
  }
  return streamChunkFromJson(parsed);
}

/** Convert collected transport chunks into the domain model (identity 1:1). */
export function toRuntimeStreamingDemo(chunks: readonly StreamChunk[]): RuntimeStreamingDemoData {
  return { chunks: [...chunks] };
}

function optionalNumber(
  source: Record<string, unknown>,
  key: string,
): number | undefined {
  const value = source[key];
  if (value === undefined) return undefined;
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`expected number at "${key}"`);
  }
  return value;
}
