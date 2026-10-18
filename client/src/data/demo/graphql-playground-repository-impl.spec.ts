import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { GraphqlPlaygroundApi } from './graphql-playground-api';
import { GraphqlPlaygroundRepositoryImpl } from './graphql-playground-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * GraphqlPlaygroundRepositoryImpl spec — fixture-driven, one endpoint at
 * a time: the package round-trips the endpoint + SDL + tour, a run
 * POSTs {"query": …} to the LIVE /api/graphql and parses both honest
 * outcome shapes (data-only, errors-with-null-data — a 200 carrying
 * errors is a successful transport), and the teaching failure paths
 * (network faults, malformed payloads, a body with neither data nor
 * errors) resolve as Failed Results, never throws.
 */

const PLAYGROUND_URL = '/api/demo/api/graphql-playground';
const GRAPHQL_URL = '/api/graphql';

const packagePayload = {
  endpoint: '/api/graphql',
  sdl: 'type Query {\n  posts: PostPage\n}',
  examples: [
    {
      id: 'page',
      label: 'A page of posts',
      description: 'The collection read.',
      query: 'query { posts { total } }',
    },
    {
      id: 'error',
      label: 'A not-found error',
      description: 'An unknown slug answers 200 with errors.',
      query: 'query { post(slug: "no-such-post") { id } }',
    },
  ],
  reasoning: 'POST /api/graphql with a JSON body like {"query": "…"} is the entire transport.',
};

const dataPayload = {
  data: { posts: { total: 12, items: [{ id: 'idempotency-retold' }] } },
};

const errorsPayload = {
  data: null,
  errors: [
    {
      message: "Post 'no-such-post' not found",
      locations: [{ line: 1, column: 3 }],
      path: ['post'],
      extensions: { code: 'not_found', slug: 'no-such-post' },
    },
  ],
};

function makeRepository(): GraphqlPlaygroundRepositoryImpl {
  return new GraphqlPlaygroundRepositoryImpl(new GraphqlPlaygroundApi(createAppConfig()));
}

describe('GraphqlPlaygroundRepositoryImpl', () => {
  it('fetches and parses the playground package', async () => {
    stubApiFetch([{ url: PLAYGROUND_URL, method: 'GET', body: packagePayload }]);

    const result = await makeRepository().playground();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.endpoint).toBe('/api/graphql');
      expect(result.value.sdl).toContain('type Query');
      expect(result.value.examples.map((example) => example.id)).toEqual(['page', 'error']);
      expect(result.value.reasoning).toContain('POST /api/graphql');
    }
  });

  it('runs a query against the live endpoint and parses a data-only answer', async () => {
    stubApiFetch([{ url: GRAPHQL_URL, method: 'POST', body: dataPayload }]);

    const result = await makeRepository().run('query { posts { total } }');

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.data).toEqual({ posts: { total: 12, items: [{ id: 'idempotency-retold' }] } });
      expect(result.value.errors).toBeUndefined();
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe('{"query":"query { posts { total } }"}');
    expect(init?.headers).toEqual(expect.objectContaining({ 'content-type': 'application/json' }));
  });

  it('parses a 200-with-errors answer as a SUCCESSFUL transport of a failed field', async () => {
    stubApiFetch([{ url: GRAPHQL_URL, method: 'POST', body: errorsPayload }]);

    const result = await makeRepository().run('query { post(slug: "no-such-post") { id } }');

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.data).toBeUndefined();
      const [error] = result.value.errors ?? [];
      expect(error?.message).toBe("Post 'no-such-post' not found");
      expect(error?.locations).toEqual([{ line: 1, column: 3 }]);
      expect(error?.path).toEqual(['post']);
      expect(error?.extensions?.code).toBe('not_found');
    }
  });

  it('rejects a response carrying neither data nor errors', async () => {
    stubApiFetch([{ url: GRAPHQL_URL, method: 'POST', body: { hello: 'world' } }]);

    const result = await makeRepository().run('query { posts { total } }');

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a non-2xx transport (empty-query 400) into a Failed Result', async () => {
    stubApiFetch([
      {
        url: GRAPHQL_URL,
        method: 'POST',
        status: 400,
        body: { errors: [{ message: 'No GraphQL query was provided' }] },
      },
    ]);

    const result = await makeRepository().run('   ');

    expect(result).toEqual(
      failed(new ServerFailure('Request failed with status 400.', { code: 'unknown_error', status: 400 })),
    );
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().playground();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
