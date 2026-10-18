import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { ValidationArenaApi } from './validation-arena-api';
import { ValidationArenaRepositoryImpl } from './validation-arena-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * ValidationArenaRepositoryImpl spec — fixture-driven, one endpoint at a
 * time: the roster round-trips the three real models with their field
 * rules, a POST round fires the model choice and candidates verbatim and
 * parses the verdict (accepted rows with coerced originals, rejected rows
 * with the envelope triples), and the teaching failure paths (422 envelope
 * on a refused round body, network faults, malformed payloads) all
 * resolve as Failed Results, never throws.
 */

const ROSTER_URL = '/api/demo/validation/arena/roster';
const ARENA_URL = '/api/demo/validation/arena';

const rosterPayload = {
  models: [
    {
      key: 'note-create',
      model: 'NoteCreate',
      source: 'guide.domain.demos.request_methods',
      description: 'The notes playground body.',
      fields: [
        { name: 'title', rule: 'str — Field(min_length=1, max_length=80), required', required: true },
        { name: 'body', rule: "str — optional, default ''", required: false },
      ],
    },
  ],
  reasoning: 'Three real wire models this server validates elsewhere.',
};

const verdictPayload = {
  model: rosterPayload.models[0],
  roster: rosterPayload.models,
  rows: [
    {
      field: 'title',
      rule: 'str — Field(min_length=1, max_length=80), required',
      required: true,
      received: { type: 'str', repr: "''" },
      outcome: {
        status: 'rejected',
        loc: ['body', 'title'],
        msg: 'String should have at least 1 character',
        type: 'string_too_short',
      },
    },
    {
      field: 'body',
      rule: "str — optional, default ''",
      required: false,
      outcome: { status: 'absent', default: '' },
    },
  ],
  verdict: 'rejected',
  errors: [
    {
      loc: ['body', 'title'],
      msg: 'String should have at least 1 character',
      type: 'string_too_short',
    },
  ],
  extraKeysIgnored: [],
  reasoning: 'pydantic refused the candidates for NoteCreate.',
};

function makeRepository(): ValidationArenaRepositoryImpl {
  return new ValidationArenaRepositoryImpl(new ValidationArenaApi(createAppConfig()));
}

describe('ValidationArenaRepositoryImpl', () => {
  it('fetches and parses the roster of real models', async () => {
    stubApiFetch([{ url: ROSTER_URL, method: 'GET', body: rosterPayload }]);

    const result = await makeRepository().roster();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.models[0]?.model).toBe('NoteCreate');
      expect(result.value.models[0]?.fields[0]?.required).toBe(true);
      expect(result.value.reasoning).toContain('Three real wire models');
    }
  });

  it('fires the round verbatim and parses the rejected verdict with its triples', async () => {
    stubApiFetch([{ url: ARENA_URL, method: 'POST', body: verdictPayload }]);

    const result = await makeRepository().run({
      model: 'note-create',
      candidates: { title: '' },
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.verdict).toBe('rejected');
      expect(result.value.errors?.[0]?.loc).toEqual(['body', 'title']);
      expect(result.value.rows[0]?.outcome.status).toBe('rejected');
      expect(result.value.validated).toBeUndefined();
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe('{"model":"note-create","candidates":{"title":""}}');
  });

  it('parses an accepted verdict with coerced originals and the validated dump', async () => {
    stubApiFetch([
      {
        url: ARENA_URL,
        method: 'POST',
        body: {
          ...verdictPayload,
          verdict: 'accepted',
          errors: undefined,
          validated: { title: 'ok', body: '', tags: [] },
          rows: [
            {
              field: 'title',
              rule: 'str',
              required: true,
              received: { type: 'str', repr: "'ok'" },
              outcome: { status: 'accepted', value: 'ok', valueType: 'str' },
            },
          ],
        },
      },
    ]);

    const result = await makeRepository().run({ model: 'note-create', candidates: { title: 'ok' } });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.verdict).toBe('accepted');
      expect(result.value.validated).toEqual({ title: 'ok', body: '', tags: [] });
      expect(result.value.errors).toBeUndefined();
    }
  });

  it('guards the 422 envelope (bogus model key) into a Failed Result', async () => {
    stubApiFetch([
      {
        url: ARENA_URL,
        method: 'POST',
        status: 422,
        body: {
          error: {
            code: 'validation_failed',
            message: 'Request validation failed.',
            requestId: 'req-422',
            details: [
              { loc: ['body', 'model'], msg: "Input should be 'note-create' or 'live'", type: 'literal_error' },
            ],
          },
        },
      },
    ]);

    const result = await makeRepository().run({
      model: 'note-create',
      candidates: {},
    });

    expect(result).toEqual(
      failed(
        new ServerFailure('Request validation failed.', {
          code: 'validation_failed',
          status: 422,
          requestId: 'req-422',
        }),
      ),
    );
  });

  it('guards a malformed verdict body into a Failed Result (invalid_response)', async () => {
    stubApiFetch([{ url: ARENA_URL, method: 'POST', body: { verdict: 'maybe' } }]);

    const result = await makeRepository().run({ model: 'note-create', candidates: {} });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().roster();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
