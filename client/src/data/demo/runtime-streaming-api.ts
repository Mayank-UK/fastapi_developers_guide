import type { AppConfig } from '../../core/config/app-config';
import {
  errorEnvelopeException,
  guardedApiCall,
} from '../../core/error-handling/guards';
import {
  InvalidResponseException,
  NetworkException,
  ServerException,
} from '../../core/error-handling/exceptions';
import type { StreamChunk } from '../../domain/demo/runtime-streaming';
import type { RuntimeStreamingDemoData } from '../../domain/demo/runtime-streaming';
import {
  streamChunkFromLine,
  toRuntimeStreamingDemo,
} from './runtime-streaming-dto';

/**
 * RuntimeStreamingApi — the transport for GET /api/demo/runtime/streaming.
 * The response is NDJSON, not one JSON document, so it cannot ride the
 * shared guardedGetJson pipeline; this adapter keeps that pipeline's
 * guarantees (fetch rejection → NetworkException, non-2xx error envelope →
 * ServerException, malformed line → InvalidResponseException) while doing
 * what the demo exists to show: consuming the stream LINE BY LINE as the
 * wire delivers it.
 *
 * When the environment's fetch exposes a ReadableStream body (browsers),
 * chunks are decoded and emitted as they arrive — the onChunk observer
 * fires progressively. Otherwise (test environments, older runtimes) the
 * body is read whole and the lines are emitted from the collected text —
 * same producer, same validation, just not incremental. The returned data
 * is identical either way.
 */

const DEMO_PATH = '/demo/runtime/streaming';

export class RuntimeStreamingApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/runtime/streaming — the NDJSON stream. */
  async get(onChunk?: (chunk: StreamChunk) => void): Promise<RuntimeStreamingDemoData> {
    return guardedApiCall(async () => {
      let response: Response;
      try {
        response = await fetch(`${this.config.apiBaseUrl}${DEMO_PATH}`, {
          headers: { accept: 'application/x-ndjson' },
        });
      } catch (error) {
        throw new NetworkException('Could not reach the server.', { cause: error });
      }

      if (!response.ok) {
        throw errorEnvelopeException(
          parseJsonOrNull(await readBodyText(response)),
          response.status,
        );
      }

      const chunks: StreamChunk[] = [];
      await readLines(response, (line) => {
        const chunk = parseChunk(line);
        chunks.push(chunk);
        onChunk?.(chunk);
      });
      return toRuntimeStreamingDemo(chunks);
    });
  }
}

/** Validate one NDJSON line, upgrading a throw to the typed wire failure. */
function parseChunk(line: string): StreamChunk {
  try {
    return streamChunkFromLine(line);
  } catch (error) {
    throw new InvalidResponseException(200, { cause: error });
  }
}

/**
 * Read the whole body as text. Streaming is pointless for an error body —
 * only its final content matters.
 */
async function readBodyText(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch (error) {
    throw new ServerException('The server response body could not be read.', {
      cause: error,
    });
  }
}

/**
 * Emit complete NDJSON lines as they arrive. Prefers the ReadableStream
 * seam (progressive); falls back to reading the full text and splitting.
 */
async function readLines(response: Response, onLine: (line: string) => void): Promise<void> {
  const body = response.body as unknown;
  if (body !== null && body !== undefined && typeof (body as { getReader?: unknown }).getReader === 'function') {
    await readStreamedLines(body as ReadableStream<Uint8Array>, onLine);
    return;
  }
  for (const line of (await readBodyText(response)).split('\n')) {
    emitLine(line, onLine);
  }
}

async function readStreamedLines(
  body: ReadableStream<Uint8Array>,
  onLine: (line: string) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = drainCompleteLines(buffer, onLine);
  }
  buffer += decoder.decode();
  emitLine(buffer, onLine);
}

/** Pop every newline-terminated line off the buffer, returning the rest. */
function drainCompleteLines(buffer: string, onLine: (line: string) => void): string {
  let rest = buffer;
  let newline = rest.indexOf('\n');
  while (newline !== -1) {
    emitLine(rest.slice(0, newline), onLine);
    rest = rest.slice(newline + 1);
    newline = rest.indexOf('\n');
  }
  return rest;
}

function emitLine(line: string, onLine: (line: string) => void): void {
  const trimmed = line.trim();
  if (trimmed !== '') onLine(trimmed);
}

/**
 * Parse an error body's text as JSON for the guards' shared envelope
 * classifier; an unparseable body is not an envelope and degrades to the
 * classifier's status-derived fallback.
 */
function parseJsonOrNull(raw: string): unknown {
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return undefined;
  }
}
