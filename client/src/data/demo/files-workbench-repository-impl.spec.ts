import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import {
  stubApiFetch,
  stubNetworkFailure,
  type StubRoute,
} from '../../test/fetch_stub';
import { FilesWorkbenchApi } from './files-workbench-api';
import { FilesWorkbenchRepositoryImpl } from './files-workbench-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * FilesWorkbenchRepositoryImpl spec — fixture-driven over the fetch stub:
 * the JSON rounds (panel, traversal) round-trip as Ok Results; the RAW
 * rounds ride their typed paths — the multipart upload (success and the
 * 422 envelope), the binary download with 206 + Content-Range shaped from
 * headers, and the ndjson stream surfaced arrival by arrival (the stub
 * answers with text, exercising the no-streaming-body fallback the real
 * transport never takes); transport failures resolve as Failed Results.
 */

const storedFileWire = {
  fileId: 'f-0a1b2c3d',
  displayName: '拍chapter.txt',
  sanitizedName: 'chapter.txt',
  declaredType: 'text/plain',
  sniffedType: 'text/plain',
  sizeBytes: 13,
  storedAt: '2026-10-17T12:00:00+00:00',
};

const panelRoute: StubRoute = {
  url: '/api/demo/files',
  body: {
    policy: {
      maxUploadBytes: 2097152,
      readChunkBytes: 65536,
      spoolThresholdBytes: 1048576,
      thumbnailMaxEdge: 96,
    },
    storedFiles: [storedFileWire],
    endpoints: [
      { path: '/api/demo/files/upload', method: 'POST', teaches: 'multipart upload' },
    ],
    honestyNotes: ['the store is IN MEMORY and demo-scoped'],
    reasoning: 'Uploads are streams validated while they are read.',
  },
};

const uploadRoute: StubRoute = {
  url: '/api/demo/files/upload',
  method: 'POST',
  body: {
    file: storedFileWire,
    sniff: {
      declaredType: 'text/plain',
      sniffedType: 'text/plain',
      agrees: true,
      note: 'declared type matches the magic bytes',
    },
    detail: 'stored as f-0a1b2c3d',
  },
};

const oversizeRoute: StubRoute = {
  url: '/api/demo/files/upload',
  method: 'POST',
  status: 422,
  body: {
    error: {
      code: 'validation_failed',
      message: 'upload rejected — body exceeds the 2097152-byte cap',
      requestId: 'req-f3',
      details: { maxUploadBytes: 2097152 },
    },
  },
};

function rangeDownloadRoute(): StubRoute {
  return {
    url: '/api/demo/files/f-0a1b2c3d/download?mode=attachment&bytes=0-19',
    status: 206,
    rawBody: 'the guide, chapter 2',
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'content-disposition': 'attachment; filename="chapter26.txt"',
      'content-range': 'bytes 0-19/46',
      'accept-ranges': 'bytes',
    },
  };
}

function streamRoute(): StubRoute {
  // One padded line, byte-exact like the server renders it: payload
  // padded to chunkBytes, plus the newline the ndjson protocol carries.
  const line = (index: number): string =>
    `{"chunk":${String(index)},"of":3,"bytes":128}`.padEnd(128, ' ');
  return {
    url: '/api/demo/files/stream?chunks=3&chunkBytes=128&paceMs=0',
    rawBody: `${line(1)}\n${line(2)}\n${line(3)}\n`,
    headers: {
      'content-type': 'application/x-ndjson',
      'x-chunk-count': '3',
      'x-chunk-bytes': '128',
      'x-pace-ms': '0',
    },
  };
}

function makeRepository(): FilesWorkbenchRepositoryImpl {
  return new FilesWorkbenchRepositoryImpl(new FilesWorkbenchApi(createAppConfig()));
}

describe('FilesWorkbenchRepositoryImpl', () => {
  it('serves the panel and the stored rows as Ok Results', async () => {
    stubApiFetch([panelRoute]);
    const result = await makeRepository().panel();
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.policy.maxUploadBytes).toBe(2097152);
      const first = result.value.storedFiles[0];
      expect(first?.sanitizedName).toBe('chapter.txt');
    }
  });

  it('uploads a File and shapes the outcome (a FormData round, not JSON)', async () => {
    stubApiFetch([uploadRoute]);
    const file = new File(['chapter bytes'], 'chapter26.txt', { type: 'text/plain' });
    const result = await makeRepository().upload(file);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.file.fileId).toBe('f-0a1b2c3d');
      expect(result.value.sniff.agrees).toBe(true);
    }
  });

  it('maps the 422 oversize envelope onto a Failed Result with its message', async () => {
    stubApiFetch([oversizeRoute]);
    const file = new File(['x'.repeat(10)], 'big.bin', { type: 'application/octet-stream' });
    const result = await makeRepository().upload(file);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.message).toContain('2097152-byte cap');
    }
  });

  it('shapes the RAW download round: 206, Content-Range, and the slice preview', async () => {
    stubApiFetch([rangeDownloadRoute()]);
    const result = await makeRepository().download('f-0a1b2c3d', 'attachment', '0-19');
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.status).toBe(206);
      expect(result.value.contentRange).toBe('bytes 0-19/46');
      expect(result.value.contentDisposition).toBe('attachment; filename="chapter26.txt"');
      expect(result.value.preview).toBe('the guide, chapter 2');
      expect(result.value.bytes).toHaveLength(20);
    }
  });

  it('surfaces every stream chunk as an arrival, then the measured outcome', async () => {
    stubApiFetch([streamRoute()]);
    const arrivals: number[] = [];
    const result = await makeRepository().stream(
      { chunkCount: 3, chunkBytes: 128, paceMs: 0 },
      (arrival) => arrivals.push(arrival.index),
    );
    expect(arrivals).toEqual([1, 2, 3]);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.plan).toEqual({ chunkCount: 3, chunkBytes: 128, paceMs: 0 });
      expect(result.value.arrivals).toHaveLength(3);
      expect(result.value.totalBytes).toBe(3 * 129); // padded line + newline
      expect(result.value.throughputBps).toBeGreaterThan(0);
    }
  });

  it('resolves transport failures as Failed Results, never throws', async () => {
    stubNetworkFailure();
    const panel = await makeRepository().panel();
    expect(panel.ok).toBe(false);
    const download = await makeRepository().download('f-0a1b2c3d', 'inline');
    expect(download.ok).toBe(false);
  });
});
