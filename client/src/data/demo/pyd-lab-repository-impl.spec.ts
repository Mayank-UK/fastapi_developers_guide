import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { PydLabApi } from './pyd-lab-api';
import { PydLabRepositoryImpl } from './pyd-lab-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * PydLabRepositoryImpl spec — fixture-driven (happy + failure): the report
 * and schema payloads round-trip into the domain shape (and the validate
 * POST carries the edited payload verbatim with an explicit JSON
 * content-type); network / envelope (including the 422 a refused body
 * earns) / malformed-payload failures all resolve as Failed Results,
 * never throws.
 */

const SCHEMA_URL = '/api/demo/pyd/lab/schema';
const VALIDATE_URL = '/api/demo/pyd/lab/validate';

const reportPayload = {
  rows: [
    {
      field: 'count',
      rule: 'int — numeric strings and whole floats coerce, lax mode',
      received: { type: 'str', repr: "'42'" },
      outcome: { status: 'coerced', value: 42, valueType: 'int', fromType: 'str' },
    },
  ],
  specimenValid: true,
  specimen: { count: 42 },
};

const schemaPayload = {
  model: 'LabSpecimen',
  jsonSchema: { title: 'LabSpecimen', properties: { score: { type: 'integer', minimum: 1 } } },
};

function makeRepository(): PydLabRepositoryImpl {
  return new PydLabRepositoryImpl(new PydLabApi(createAppConfig()));
}

describe('PydLabRepositoryImpl', () => {
  it('submits the payload verbatim with the JSON content type and returns a Success', async () => {
    let seenInit: RequestInit | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        seenInit = init;
        return { ok: true, status: 200, json: async () => reportPayload };
      }),
    );

    const payload = { count: '42', flag: 'true', tags: ['x'], score: '100', handle: ' Grace Hopper ' };
    const result = await makeRepository().validate(payload);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.rows).toHaveLength(1);
      expect(result.value.rows[0]?.field).toBe('count');
      expect(result.value.specimenValid).toBe(true);
      expect(result.value.specimen).toEqual({ count: 42 });
    }
    expect(seenInit?.method).toBe('POST');
    expect(seenInit?.headers).toEqual({
      accept: 'application/json',
      'content-type': 'application/json',
    });
    expect(seenInit?.body).toBe(JSON.stringify(payload));
  });

  it('fetches the generated schema through the guarded GET pipeline', async () => {
    stubApiFetch([{ url: SCHEMA_URL, body: schemaPayload }]);

    const result = await makeRepository().schema();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.model).toBe('LabSpecimen');
      expect(result.value.jsonSchema['title']).toBe('LabSpecimen');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().validate({ count: 1 });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards the 422 envelope a refused body earns into a Failed Result', async () => {
    stubApiFetch([
      {
        url: VALIDATE_URL,
        status: 422,
        body: {
          error: {
            code: 'validation_failed',
            message: 'Request validation failed.',
            requestId: 'req-31',
            details: [{ loc: ['body', 'tags'], msg: ' Input should be a valid list.', type: 'list_type' }],
          },
        },
      },
    ]);

    const result = await makeRepository().validate({ tags: 'oops' });

    expect(result).toEqual(
      failed(
        new ServerFailure('Request validation failed.', {
          code: 'validation_failed',
          status: 422,
          requestId: 'req-31',
        }),
      ),
    );
  });

  it('guards a malformed report into a Failed Result (invalid_response)', async () => {
    stubApiFetch([
      // An unknown outcome status must be rejected by the DTO validator.
      {
        url: VALIDATE_URL,
        body: {
          rows: [
            {
              field: 'count',
              rule: 'int',
              received: { type: 'str', repr: "'42'" },
              outcome: { status: 'mystery', value: 42, valueType: 'int' },
            },
          ],
          specimenValid: true,
        },
      },
    ]);

    const result = await makeRepository().validate({});

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
