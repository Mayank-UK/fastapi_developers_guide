import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { RuntimeTypesApi } from './runtime-types-api';
import { RuntimeTypesRepositoryImpl } from './runtime-types-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * RuntimeTypesRepositoryImpl spec — fixture-driven (happy + failure): the
 * happy payload round-trips into the domain shape; network / envelope /
 * malformed-payload failures all resolve as Failed Results, never throws.
 */

/** A minimal but structurally complete wire payload. */
const demoPayload = {
  hintsVsRaw: [
    {
      symbol: 'guide.domain.demos.runtime_types.repeat',
      mode: 'deferred',
      rows: [
        { name: 'text', raw: "'str'", resolved: 'str' },
        { name: 'times', raw: "'int'", resolved: 'int' },
        { name: 'return', raw: "'str'", resolved: 'str' },
      ],
    },
    {
      symbol: 'guide.content.registry.ContentRegistry.topic_by_id',
      mode: 'eager',
      rows: [
        { name: 'topic_id', raw: 'str', resolved: 'str' },
        { name: 'return', raw: 'Topic | None', resolved: 'Topic | None' },
      ],
    },
  ],
  originArgs: [
    { symbol: 'list[int]', alias: 'list[int]', origin: 'list', args: ['int'] },
  ],
  faceOff: {
    dataclassSymbol: 'guide.content.snippet_matcher.SnippetMatch',
    dataclassFields: [
      { name: 'ok', annotation: 'bool', required: true },
      { name: 'reason', annotation: 'str | None', required: false },
    ],
    pydanticSymbol: 'guide.content.models.Topic',
    pydanticFields: [
      { name: 'id', annotation: 'str', required: true },
      { name: 'subtitle', annotation: 'str | None', required: false },
    ],
  },
  enforcement: {
    function: 'repeat',
    signature: 'def repeat(text: str, times: int) -> str',
    call: 'repeat(3.0, 2)',
    declaredReturn: 'str',
    actualReturn: 'float',
    returnedValue: '6.0',
    mypyVerdict: 'Argument 1 to "repeat" has incompatible type "float"; expected "str"',
  },
  boundary: {
    model: 'Topic',
    badInput: '{"id": 123, …}',
    outcome: 'rejected',
    errorType: 'string_type',
    message: 'Input should be a valid string',
  },
};

function makeRepository(): RuntimeTypesRepositoryImpl {
  return new RuntimeTypesRepositoryImpl(new RuntimeTypesApi(createAppConfig()));
}

describe('RuntimeTypesRepositoryImpl', () => {
  it('returns a Success carrying the validated domain payload', async () => {
    stubApiFetch([{ url: '/api/demo/py/runtime-types', body: demoPayload }]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.enforcement.returnedValue).toBe('6.0');
      expect(result.value.hintsVsRaw[0]?.mode).toBe('deferred');
      expect(result.value.faceOff.pydanticFields[1]?.required).toBe(false);
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

  it('guards an error envelope into a Failed Result with its diagnostics', async () => {
    stubApiFetch([
      {
        url: '/api/demo/py/runtime-types',
        status: 503,
        body: { error: { code: 'service_unavailable', message: 'calm down', requestId: 'req-9' } },
      },
    ]);

    const result = await makeRepository().get();

    expect(result).toEqual(
      failed(
        new ServerFailure('calm down', {
          code: 'service_unavailable',
          status: 503,
          requestId: 'req-9',
        }),
      ),
    );
  });

  it('guards a malformed payload into a Failed Result (invalid_response)', async () => {
    stubApiFetch([
      // Missing every section — the DTO validator must reject it.
      { url: '/api/demo/py/runtime-types', body: { hintsVsRaw: 'nope' } },
    ]);

    const result = await makeRepository().get();

    expect(result).toEqual(
      failed(
        new ServerFailure('The server response did not match the expected shape.', {
          code: 'invalid_response',
          status: 200,
        }),
      ),
    );
  });

  it('rejects an unknown symbol mode instead of letting it through', async () => {
    stubApiFetch([
      {
        url: '/api/demo/py/runtime-types',
        body: { ...demoPayload, hintsVsRaw: [{ symbol: 'x', mode: 'lazy', rows: [] }] },
      },
    ]);

    const result = await makeRepository().get();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
