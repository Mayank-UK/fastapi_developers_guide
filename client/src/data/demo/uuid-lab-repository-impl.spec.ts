import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { UuidLabApi } from './uuid-lab-api';
import { UuidLabRepositoryImpl } from './uuid-lab-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * UuidLabRepositoryImpl spec — fixture-driven: the payload round-trips
 * (runs with ranks, layout dissection, strategy cards), optional
 * randomBits stays undefined when absent, malformed payloads resolve as
 * Failed Results, never throws.
 */

const LAB_URL = '/api/demo/db/uuid';

const labPayload = {
  sampleCount: 12,
  runs: [
    {
      kind: 'uuid4',
      values: ['93e32229-e07a-467f-b136-2640ab681caa', '086fdb6a-7dcd-4a73-809e-ebd3436be5a5'],
      sortRanks: [1, 0],
      sortable: false,
    },
    {
      kind: 'uuid7',
      values: ['01a14438-4d32-72e5-8000-000000087d33', '01a14438-4d32-72e5-8000-000040878f2a'],
      sortRanks: [0, 1],
      sortable: true,
    },
    {
      kind: 'sequence',
      values: ['1', '2', '10'],
      sortRanks: [0, 2, 1],
      sortable: false,
    },
  ],
  sharedPrefixHex: '01a14438-4d32-72e5-8000-0000',
  layout: {
    value: '01a14438-4d32-72e5-8000-000000087d33',
    unixMs: 1792145902898,
    generatedAtIso: '2026-10-16T10:18:22.898000+00:00',
    segments: [
      { label: 'unix_ms', hexValue: '01a144384d32', bits: 48, meaning: 'milliseconds since epoch' },
      { label: 'version', hexValue: '7', bits: 4, meaning: 'always 7' },
    ],
  },
  strategies: [
    {
      id: 'sequence',
      name: 'bigserial (sequence)',
      sortableAsText: false,
      indexLocality: 'perfect',
      randomBits: 0,
      coordination: 'the database mints it',
      leaksTiming: true,
    },
    {
      id: 'uuid7',
      name: 'UUIDv7 (time-ordered)',
      sortableAsText: true,
      indexLocality: 'good',
      randomBits: 74,
      coordination: 'none',
      leaksTiming: true,
    },
  ],
  reasoning: 'All 12 UUIDv7s were minted inside one millisecond.',
};

function makeRepository(): UuidLabRepositoryImpl {
  return new UuidLabRepositoryImpl(new UuidLabApi(createAppConfig()));
}

describe('UuidLabRepositoryImpl', () => {
  it('fetches and parses the freshly minted lab payload', async () => {
    stubApiFetch([{ url: LAB_URL, method: 'GET', body: labPayload }]);

    const result = await makeRepository().lab();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.sampleCount).toBe(12);
      const [uuid4Run, uuid7Run, sequenceRun] = result.value.runs;
      expect(uuid4Run?.sortable).toBe(false);
      expect(uuid7Run?.sortRanks).toEqual([0, 1]);
      expect(sequenceRun?.values).toEqual(['1', '2', '10']);
      expect(result.value.layout.segments[0]).toEqual({
        label: 'unix_ms',
        hexValue: '01a144384d32',
        bits: 48,
        meaning: 'milliseconds since epoch',
      });
      expect(result.value.strategies[1]?.randomBits).toBe(74);
      expect(result.value.sharedPrefixHex).toContain('01a14438');
    }
  });

  it('rejects a run whose sortRanks carry a non-integer', async () => {
    const poisoned = {
      ...labPayload,
      runs: [{ ...labPayload.runs[0], sortRanks: [0.5, 0] }],
    };
    stubApiFetch([{ url: LAB_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().lab();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('rejects a payload without a layout object', async () => {
    const { layout, ...withoutLayout } = labPayload;
    void layout;
    stubApiFetch([{ url: LAB_URL, method: 'GET', body: withoutLayout }]);

    const result = await makeRepository().lab();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().lab();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
