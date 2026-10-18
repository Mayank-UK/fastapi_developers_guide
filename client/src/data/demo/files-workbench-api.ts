import type { AppConfig } from '../../core/config/app-config';
import { NetworkException } from '../../core/error-handling/exceptions';
import {
  guardedApiCall,
  guardedGetJson,
  guardedSendJson,
  parseDto,
  readHeader,
  responseEnvelopeException,
} from '../../core/error-handling/guards';
import type {
  DownloadMode,
  DownloadRound,
  ImageVariantsRow,
  StreamChunkArrival,
  StreamOutcome,
  StoredFilesInventory,
  TraversalRow,
  UploadOutcome,
  FilesWorkbenchPanel,
} from '../../domain/demo/files-workbench';
import {
  filesWorkbenchPanelFromJson,
  imageVariantsFromJson,
  storedFilesFromJson,
  traversalRowFromJson,
  uploadOutcomeFromJson,
} from './files-workbench-dto';

/**
 * FilesWorkbenchApi — the transport for the workbench's endpoints.
 *
 * The JSON rounds (panel, stored, traversal) ride the shared guarded
 * pipeline. The other four are RAW rounds, each for a structural reason:
 * UPLOAD posts a FormData (multipart bodies cannot ride the JSON guard),
 * DOWNLOAD answers BYTES with meaningful headers (a binary body has no
 * JSON to validate), and STREAM is consumed as it arrives (the lesson IS
 * the cadence, so nothing may buffer it whole). This follows the raw-round
 * precedent the security lab set for its 429: shape the outcome from
 * status + headers + body, and guard every failure into the shared
 * taxonomy — the JSON pipeline is not forced onto responses it cannot
 * represent.
 */

const PANEL_PATH = '/demo/files';
const STORED_PATH = '/demo/files/stored';
const UPLOAD_PATH = '/demo/files/upload';
const IMAGES_PATH = '/demo/files/images';
const TRAVERSAL_PATH = '/demo/files/traversal';
const STREAM_PATH = '/demo/files/stream';

export class FilesWorkbenchApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/files — the panel (policy, inventory, tour). */
  async panel(): Promise<FilesWorkbenchPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, filesWorkbenchPanelFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/files/stored — the store's inventory. */
  async stored(): Promise<StoredFilesInventory> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, STORED_PATH);
      return parseDto(body, status, storedFilesFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/files/upload — one multipart file upload. */
  async upload(file: File): Promise<UploadOutcome> {
    return guardedApiCall(async () => {
      const response = await this.postForm(UPLOAD_PATH, file);
      if (response.status !== 200) {
        throw await responseEnvelopeException(response);
      }
      return uploadOutcomeFromJson(await response.json());
    });
  }

  /** POST {apiBaseUrl}/demo/files/images — the Pillow variants round. */
  async processImage(file: File): Promise<ImageVariantsRow> {
    return guardedApiCall(async () => {
      const response = await this.postForm(IMAGES_PATH, file);
      if (response.status !== 200) {
        throw await responseEnvelopeException(response);
      }
      return imageVariantsFromJson(await response.json());
    });
  }

  /**
   * GET {apiBaseUrl}/demo/files/{id}/download — one RAW binary round.
   * 200 answers the full body; 206 answers the exact slice with its
   * Content-Range; anything else is guarded into the shared taxonomy.
   */
  async download(
    fileId: string,
    mode: DownloadMode,
    bytesWindow?: string,
  ): Promise<DownloadRound> {
    return guardedApiCall(async () => {
      const query = `?mode=${mode}${bytesWindow ? `&bytes=${bytesWindow}` : ''}`;
      let response: Response;
      try {
        response = await fetch(
          `${this.config.apiBaseUrl}${PANEL_PATH}/${fileId}/download${query}`,
          { headers: { accept: '*/*' } },
        );
      } catch (error) {
        throw new NetworkException('Could not reach the server.', { cause: error });
      }
      if (response.status !== 200 && response.status !== 206) {
        throw await responseEnvelopeException(response);
      }
      const bytes = new Uint8Array(await readBodyBytes(response));
      return {
        status: response.status,
        bytes,
        contentType: readHeader(response.headers, 'content-type') ?? '',
        contentDisposition: readHeader(response.headers, 'content-disposition') ?? '',
        contentRange: readHeader(response.headers, 'content-range') ?? null,
        acceptRanges: readHeader(response.headers, 'accept-ranges') ?? null,
        preview: printablePreview(bytes),
      };
    });
  }

  /** POST {apiBaseUrl}/demo/files/traversal — one name through the defense. */
  async testTraversal(name: string): Promise<TraversalRow> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, TRAVERSAL_PATH, {
        method: 'POST',
        body: JSON.stringify({ name }),
      });
      return parseDto(body, status, traversalRowFromJson);
    });
  }

  /**
   * GET {apiBaseUrl}/demo/files/stream — the paced ndjson stream, consumed
   * AS IT ARRIVES. Each complete line becomes one arrival (timed against
   * the round's start) surfaced through `onArrival`; the finished round
   * carries the plan, the arrivals, and the measured throughput. An
   * abort signal lets the panel offer a stop button mid-stream.
   */
  async stream(
    plan: { chunkCount: number; chunkBytes: number; paceMs: number },
    onArrival: (arrival: StreamChunkArrival) => void,
    signal?: AbortSignal,
  ): Promise<StreamOutcome> {
    return guardedApiCall(async () => {
      const query = `?chunks=${plan.chunkCount}&chunkBytes=${plan.chunkBytes}&paceMs=${plan.paceMs}`;
      let response: Response;
      try {
        response = await fetch(`${this.config.apiBaseUrl}${STREAM_PATH}${query}`, {
          headers: { accept: 'application/x-ndjson' },
          signal,
        });
      } catch (error) {
        throw new NetworkException('Could not reach the server.', { cause: error });
      }
      if (response.status !== 200) {
        throw await responseEnvelopeException(response);
      }
      const planFromHeaders = {
        chunkCount: Number(readHeader(response.headers, 'x-chunk-count') ?? plan.chunkCount),
        chunkBytes: Number(readHeader(response.headers, 'x-chunk-bytes') ?? plan.chunkBytes),
        paceMs: Number(readHeader(response.headers, 'x-pace-ms') ?? plan.paceMs),
      };
      const startedAt = nowMs();
      const arrivals: StreamChunkArrival[] = [];
      let totalBytes = 0;
      for await (const line of streamLines(response)) {
        const parsed = JSON.parse(line) as { chunk: number; of: number; bytes: number };
        const arrival: StreamChunkArrival = {
          index: parsed.chunk,
          of: parsed.of,
          bytes: parsed.bytes,
          elapsedMs: Math.round(nowMs() - startedAt),
          text: line.trim(),
        };
        arrivals.push(arrival);
        totalBytes += line.length + 1; // the line plus its newline
        onArrival(arrival);
      }
      const elapsedMs = Math.max(1, Math.round(nowMs() - startedAt));
      return {
        plan: planFromHeaders,
        arrivals,
        totalBytes,
        elapsedMs,
        throughputBps: Math.round((totalBytes / elapsedMs) * 1000),
        aborted: signal?.aborted ?? false,
      };
    });
  }

  private async postForm(path: string, file: File): Promise<Response> {
    const form = new FormData();
    form.append('file', file, file.name);
    try {
      return await fetch(`${this.config.apiBaseUrl}${path}`, {
        method: 'POST',
        body: form,
      });
    } catch (error) {
      throw new NetworkException('Could not reach the server.', { cause: error });
    }
  }
}

/** The body's bytes — arrayBuffer when the transport offers it, text otherwise. */
async function readBodyBytes(response: Response): Promise<ArrayBuffer> {
  const asBuffer = (response as Partial<Response>).arrayBuffer;
  if (typeof asBuffer === 'function') {
    return asBuffer.call(response);
  }
  const text = await response.text();
  return new TextEncoder().encode(text).buffer as ArrayBuffer;
}

/** Yield each complete ndjson line as it arrives — never buffering the whole body. */
async function* streamLines(response: Response): AsyncGenerator<string> {
  const body = (response as Partial<Response>).body;
  if (body !== undefined && body !== null && typeof body.getReader === 'function') {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline = buffer.indexOf('\n');
      while (newline !== -1) {
        yield buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        newline = buffer.indexOf('\n');
      }
    }
    if (buffer.length > 0) yield buffer;
    return;
  }
  // No streaming body (test stand-ins): the same line protocol over text().
  for (const line of (await response.text()).split('\n')) {
    if (line.length > 0) yield line;
  }
}

/** The first bytes as printable text — the slice proof the panel shows. */
function printablePreview(bytes: Uint8Array): string {
  const head = new TextDecoder('utf-8', { fatal: false }).decode(bytes.slice(0, 48));
  const printable = head.replace(/[^\x20-\x7E]/g, '·');
  return bytes.length > 48 ? `${printable}…` : printable;
}

function nowMs(): number {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}
