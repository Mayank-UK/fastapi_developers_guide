import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import type { StreamChunk } from '../../domain/demo/runtime-streaming';
import { RuntimeStreamingApi } from './runtime-streaming-api';
import { RuntimeStreamingRepositoryImpl } from './runtime-streaming-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * RuntimeStreamingRepositoryImpl spec — fixture-driven over the raw-NDJSON
 * seam (fetch stub with rawBody): every line round-trips into the domain,
 * the observer receives chunks in arrival order, and network / envelope /
 * malformed-line failures resolve as Failed Results, never throws.
 */

const openLine =
  '{"seq":0,"kind":"open","label":"runtime-stream","detail":"6 items follow, one per awaited tick"}';
const itemLine = (index: number) =>
  `{"seq":${String(index)},"kind":"item","label":"loop-tick-${String(index)}","detail":"yielded after 2ms of simulated io"}`;
const closedLine =
  '{"seq":7,"kind":"closed","label":"stream-complete","itemsDelivered":6,"totalMs":15.3}';

const streamBody = [
  openLine,
  ...[1, 2, 3, 4, 5, 6].map(itemLine),
  closedLine,
].join('\n');

function makeRepository(): RuntimeStreamingRepositoryImpl {
  return new RuntimeStreamingRepositoryImpl(new RuntimeStreamingApi(createAppConfig()));
}

describe('RuntimeStreamingRepositoryImpl', () => {
  it('collects the full stream and fires the observer per line, in order', async () => {
    stubApiFetch([{ url: '/api/demo/runtime/streaming', rawBody: streamBody }]);

    const observed: StreamChunk[] = [];
    const result = await makeRepository().get((chunk) => observed.push(chunk));

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.chunks).toHaveLength(8);
      expect(result.value.chunks[0]).toMatchObject({ seq: 0, kind: 'open' });
      expect(result.value.chunks[7]).toMatchObject({
        kind: 'closed',
        itemsDelivered: 6,
        totalMs: 15.3,
      });
      expect(observed.map((chunk) => chunk.seq)).toEqual([0, 1, 2, 3, 4, 5, 6, 7]);
      expect(observed).toEqual(result.value.chunks);
    }
  });

  it('works without an observer (collected result only)', async () => {
    stubApiFetch([{ url: '/api/demo/runtime/streaming', rawBody: streamBody }]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.chunks.map((chunk) => chunk.kind)).toEqual([
        'open',
        ...Array.from({ length: 6 }, () => 'item'),
        'closed',
      ]);
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().get();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards a non-2xx error envelope into a Failed Result with its diagnostics', async () => {
    stubApiFetch([
      {
        url: '/api/demo/runtime/streaming',
        status: 503,
        rawBody: JSON.stringify({
          error: { code: 'service_unavailable', message: 'calm down', requestId: 'req-4' },
        }),
      },
    ]);

    const result = await makeRepository().get();

    expect(result).toEqual(
      failed(
        new ServerFailure('calm down', {
          code: 'service_unavailable',
          status: 503,
          requestId: 'req-4',
        }),
      ),
    );
  });

  it('guards a malformed NDJSON line into a Failed Result (invalid_response)', async () => {
    stubApiFetch([
      { url: '/api/demo/runtime/streaming', rawBody: `${openLine}\nnot-json\n` },
    ]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
      expect(result.failure.status).toBe(200);
    }
  });

  it('rejects an unknown chunk kind instead of letting it through', async () => {
    stubApiFetch([
      {
        url: '/api/demo/runtime/streaming',
        rawBody: '{"seq":0,"kind":"surprise","label":"x"}\n',
      },
    ]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
