import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { PostsWorkbenchApi } from './posts-workbench-api';
import { PostsWorkbenchRepositoryImpl } from './posts-workbench-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * PostsWorkbenchRepositoryImpl spec — fixture-driven, one endpoint at a
 * time: the roster round-trips the substrate's facets, a POST round
 * fires the picked request verbatim and parses the outcome (a traced
 * list with page + pagination + layers, a 404 envelope with the round's
 * own request id, a 405 for DELETE), and the teaching failure paths
 * (422 envelope on a refused combination, network faults, malformed
 * payloads) all resolve as Failed Results, never throws.
 */

const WORKBENCH_URL = '/api/demo/api/workbench';

const rosterPayload = {
  authors: ['alan', 'barbara', 'grace'],
  tags: ['api', 'design'],
  statuses: ['draft', 'published'],
  sorts: ['newest', 'oldest', 'title'],
  totalPosts: 12,
  reasoning: 'The workbench runs over the REAL /api/posts substrate.',
};

const listOutcomePayload = {
  operation: 'list',
  request: { method: 'GET', template: '/api/posts', path: '/api/posts?page=2&limit=4' },
  status: 200,
  statusReason: '200 OK',
  kind: 'page',
  page: {
    items: [
      {
        id: 'filtering-without-surprises',
        title: 'Filtering without surprises',
        body: 'Exact-match filters.',
        author: 'barbara',
        tags: ['api'],
        status: 'published',
        createdAt: '2026-09-06T08:00:00.000+00:00',
        updatedAt: '2026-09-06T08:00:00.000+00:00',
      },
    ],
    total: 12,
    page: 2,
    limit: 4,
    pages: 3,
  },
  pagination: { total: 12, page: 2, limit: 4, pages: 3, next: '/api/posts?page=3&limit=4' },
  layers: [
    { name: 'routing', detail: 'GET /api/posts matched the collection route.' },
    { name: 'validation', detail: 'Query bound through PostListQuery.' },
    { name: 'use case', detail: 'ListPostsUseCase.execute ran.' },
    { name: 'repository', detail: 'Filtered, sorted, sliced.' },
    { name: 'response', detail: 'PostPage serialized; headers stamped.' },
  ],
  reasoning: 'The real GET /api/posts answers 200 with this page.',
};

const envelopeOutcomePayload = {
  operation: 'get',
  request: {
    method: 'GET',
    template: '/api/posts/{postId}',
    path: '/api/posts/nope',
  },
  status: 404,
  statusReason: '404 Not Found',
  kind: 'envelope',
  envelope: { code: 'not_found', message: "Post 'nope' not found", requestId: 'req-1' },
  layers: [
    { name: 'routing', detail: 'matched the item route.' },
    { name: 'validation', detail: 'path parameter is a str.' },
    { name: 'use case', detail: 'GetPostUseCase returned Err(not_found).' },
    { name: 'response', detail: 'the shared handler rendered the envelope.' },
  ],
  reasoning: 'The real GET would answer 404 with this exact envelope.',
};

function makeRepository(): PostsWorkbenchRepositoryImpl {
  return new PostsWorkbenchRepositoryImpl(new PostsWorkbenchApi(createAppConfig()));
}

describe('PostsWorkbenchRepositoryImpl', () => {
  it('fetches and parses the roster of live facets', async () => {
    stubApiFetch([{ url: WORKBENCH_URL, method: 'GET', body: rosterPayload }]);

    const result = await makeRepository().roster();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.authors).toEqual(['alan', 'barbara', 'grace']);
      expect(result.value.statuses).toEqual(['draft', 'published']);
      expect(result.value.totalPosts).toBe(12);
      expect(result.value.reasoning).toContain('REAL /api/posts');
    }
  });

  it('fires the round verbatim and parses a traced list outcome', async () => {
    stubApiFetch([{ url: WORKBENCH_URL, method: 'POST', body: listOutcomePayload }]);

    const round = {
      method: 'GET',
      template: '/api/posts',
      query: { page: 2, limit: 4, sort: 'newest' },
    } as const;
    const result = await makeRepository().run(round);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.operation).toBe('list');
      expect(result.value.request.path).toBe('/api/posts?page=2&limit=4');
      expect(result.value.page?.items[0]?.id).toBe('filtering-without-surprises');
      expect(result.value.pagination?.next).toBe('/api/posts?page=3&limit=4');
      expect(result.value.pagination?.prev).toBeUndefined();
      expect(result.value.layers.map((layer) => layer.name)).toEqual([
        'routing',
        'validation',
        'use case',
        'repository',
        'response',
      ]);
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe('{"method":"GET","template":"/api/posts","query":{"page":2,"limit":4,"sort":"newest"}}');
  });

  it('parses a 404 envelope outcome with the round request id', async () => {
    stubApiFetch([{ url: WORKBENCH_URL, method: 'POST', body: envelopeOutcomePayload }]);

    const result = await makeRepository().run({
      method: 'GET',
      template: '/api/posts/{postId}',
      postId: 'nope',
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.status).toBe(404);
      expect(result.value.kind).toBe('envelope');
      expect(result.value.envelope?.code).toBe('not_found');
      expect(result.value.envelope?.requestId).toBe('req-1');
      expect(result.value.post).toBeUndefined();
    }
  });

  it('guards the 422 envelope (item template without a postId) into a Failed Result', async () => {
    stubApiFetch([
      {
        url: WORKBENCH_URL,
        method: 'POST',
        status: 422,
        body: {
          error: {
            code: 'validation_failed',
            message: 'Request validation failed.',
            requestId: 'req-422',
            details: [{ loc: ['body'], msg: 'post_id is required with the item template', type: 'value_error' }],
          },
        },
      },
    ]);

    const result = await makeRepository().run({ method: 'GET', template: '/api/posts/{postId}' });

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

  it('guards a malformed outcome body into a Failed Result (invalid_response)', async () => {
    stubApiFetch([{ url: WORKBENCH_URL, method: 'POST', body: { kind: 'maybe' } }]);

    const result = await makeRepository().run({ method: 'GET', template: '/api/posts' });

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
