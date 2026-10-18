import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { ReqresMethodsApi } from './reqres-methods-api';
import { ReqresMethodsRepositoryImpl } from './reqres-methods-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * ReqresMethodsRepositoryImpl spec — fixture-driven, one verb at a time:
 * the listing round-trips filtered (no revision key anywhere), POST composes
 * the 201 exchange from the response's status AND its Location header, PUT
 * parses the replaced body, DELETE resolves 204 No Content as a bodyless
 * success exchange, and the teaching failure paths (404 envelope on an
 * unknown id, 422 envelope on an invalid body) plus network faults all
 * resolve as Failed Results, never throws.
 */

const LIST_URL = '/api/demo/reqres/notes';

const listingPayload = {
  count: 1,
  notes: [
    {
      id: 1,
      title: 'Read the request first',
      body: 'line, query, headers.',
      tags: ['request'],
      createdAt: '2026-10-15T10:00:00.000+00:00',
    },
  ],
  reasoning: 'GET answered 200 with all 1 notes filtered through NotePublic.',
};

const notePayload = {
  id: 3,
  title: 'created by spec',
  body: 'b',
  tags: ['t'],
  createdAt: '2026-10-15T10:00:02.000+00:00',
};

function makeRepository(): ReqresMethodsRepositoryImpl {
  return new ReqresMethodsRepositoryImpl(new ReqresMethodsApi(createAppConfig()));
}

describe('ReqresMethodsRepositoryImpl', () => {
  it('lists through the filtered public view', async () => {
    stubApiFetch([{ url: LIST_URL, method: 'GET', body: listingPayload }]);

    const result = await makeRepository().list();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.status).toBe(200);
      expect(result.value.method).toBe('GET');
      expect(result.value.listing?.notes[0]?.title).toBe('Read the request first');
      expect('revision' in (result.value.listing?.notes[0] ?? {})).toBe(false);
    }
  });

  it('composes the 201 exchange with the Location header from the wire', async () => {
    stubApiFetch([
      {
        url: LIST_URL,
        method: 'POST',
        status: 201,
        headers: { location: '/api/demo/reqres/notes/3' },
        body: notePayload,
      },
    ]);

    const result = await makeRepository().create({ title: 'created by spec', body: 'b', tags: ['t'] });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.status).toBe(201);
      expect(result.value.location).toBe('/api/demo/reqres/notes/3');
      expect(result.value.note?.id).toBe(3);
      expect('revision' in (result.value.note ?? {})).toBe(false);
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe('{"title":"created by spec","body":"b","tags":["t"]}');
  });

  it('replaces via PUT and parses the replaced body', async () => {
    stubApiFetch([{ url: `${LIST_URL}/2`, method: 'PUT', body: { ...notePayload, id: 2 } }]);

    const result = await makeRepository().replace(2, { title: 'after', body: '', tags: [] });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.method).toBe('PUT');
      expect(result.value.status).toBe(200);
      expect(result.value.note?.id).toBe(2);
      expect(result.value.note?.title).toBe('created by spec');
    }
  });

  it('resolves 204 No Content as a bodyless success exchange', async () => {
    stubApiFetch([{ url: `${LIST_URL}/2`, method: 'DELETE', status: 204, body: undefined }]);

    const result = await makeRepository().remove(2);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.method).toBe('DELETE');
      expect(result.value.status).toBe(204);
      expect(result.value.note).toBeUndefined();
      expect(result.value.listing).toBeUndefined();
    }
  });

  it('guards the 404 envelope (unknown id) into a Failed Result', async () => {
    stubApiFetch([
      {
        url: `${LIST_URL}/99`,
        method: 'DELETE',
        status: 404,
        body: { error: { code: 'not_found', message: 'Note 99 not found', requestId: 'req-9' } },
      },
    ]);

    const result = await makeRepository().remove(99);

    expect(result).toEqual(
      failed(
        new ServerFailure('Note 99 not found', {
          code: 'not_found',
          status: 404,
          requestId: 'req-9',
        }),
      ),
    );
  });

  it('guards the 422 envelope (invalid body) into a Failed Result', async () => {
    stubApiFetch([
      {
        url: LIST_URL,
        method: 'POST',
        status: 422,
        body: {
          error: {
            code: 'validation_failed',
            message: 'Request validation failed.',
            requestId: 'req-10',
            details: [{ loc: ['body', 'title'], msg: 'String should have at least 1 character', type: 'string_too_short' }],
          },
        },
      },
    ]);

    const result = await makeRepository().create({ title: '', body: '', tags: [] });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('validation_failed');
      expect(result.failure.status).toBe(422);
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().list();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });

  it('guards a malformed note body into a Failed Result (invalid_response)', async () => {
    stubApiFetch([
      { url: LIST_URL, method: 'GET', body: listingPayload },
      { url: LIST_URL, method: 'POST', status: 201, body: { ...notePayload, id: 'three' } },
    ]);

    const repository = makeRepository();
    await repository.list();
    const result = await repository.create({ title: 'x', body: '', tags: [] });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });
});
