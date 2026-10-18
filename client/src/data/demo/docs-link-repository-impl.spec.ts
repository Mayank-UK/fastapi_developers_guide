import { afterEach, describe, expect, it, vi } from 'vitest';
import { ServerFailure } from '../../core/error-handling/failures';
import { failed } from '../../core/result';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DocsLinkApi } from './docs-link-api';
import { DocsLinkRepositoryImpl } from './docs-link-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * DocsLinkRepositoryImpl spec — fixture-driven, one endpoint: the hub
 * payload round-trips (links, counts, areas, the posts operations, and
 * the showcase slice with its $ref names), a disabled docs mount stays
 * honestly absent, and the failure paths (a 500 envelope, network
 * faults, malformed payloads) all resolve as Failed Results, never
 * throws.
 */

const DOCS_LINK_URL = '/api/demo/api/docs-link';

const hubPayload = {
  infoTitle: 'FastAPI Developers Guide',
  infoVersion: '0.1.0',
  openapiVersion: '3.1.0',
  docs: { swaggerUi: '/docs', redoc: '/redoc', openapiJson: '/openapi.json' },
  pathCount: 25,
  operationCount: 34,
  areaCount: 15,
  areas: [
    { tag: 'content', paths: 2, operations: 2, methods: ['GET'] },
    { tag: 'posts', paths: 2, operations: 4, methods: ['GET', 'POST', 'PUT'] },
  ],
  schemaCount: 93,
  schemaNames: ['HTTPValidationError', 'Post', 'PostCreate'],
  postsOperations: [
    {
      method: 'GET',
      path: '/api/posts',
      operationId: 'list_posts_api_posts_get',
      summary: 'List Posts',
      description: 'Serve one filtered, sorted, paginated page.',
      responses: ['200', '422'],
    },
    {
      method: 'POST',
      path: '/api/posts',
      operationId: 'create_post_api_posts_post',
      summary: 'Create Post',
      description: 'Create from the validated body: 201 + Location names the resource.',
      responses: ['201', '422'],
    },
  ],
  showcase: {
    method: 'POST',
    path: '/api/posts',
    summary: 'Create Post',
    description: 'Create from the validated body: 201 + Location names the resource.',
    operationId: 'create_post_api_posts_post',
    tags: ['posts'],
    requestSchema: 'PostCreate',
    successStatus: '201',
    successSchema: 'Post',
    validationSchema: 'HTTPValidationError',
  },
  reasoning:
    'Every fact here was read from the same OpenAPI document the running app serves at /openapi.json.',
};

function makeRepository(): DocsLinkRepositoryImpl {
  return new DocsLinkRepositoryImpl(new DocsLinkApi(createAppConfig()));
}

describe('DocsLinkRepositoryImpl', () => {
  it('fetches and parses the documentation hub', async () => {
    stubApiFetch([{ url: DOCS_LINK_URL, method: 'GET', body: hubPayload }]);

    const result = await makeRepository().hub();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.docs).toEqual({
        swaggerUi: '/docs',
        redoc: '/redoc',
        openapiJson: '/openapi.json',
      });
      expect(result.value.pathCount).toBe(25);
      expect(result.value.postsOperations).toHaveLength(2);
      expect(result.value.showcase?.requestSchema).toBe('PostCreate');
      expect(result.value.showcase?.successStatus).toBe('201');
      expect(result.value.reasoning).toContain('/openapi.json');
    }
  });

  it('keeps a disabled docs mount absent instead of inventing a link', async () => {
    stubApiFetch([
      {
        url: DOCS_LINK_URL,
        method: 'GET',
        body: { ...hubPayload, docs: {} },
      },
    ]);

    const result = await makeRepository().hub();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.docs).toEqual({});
    }
  });

  it('parses a hub without a showcase slice (schema lacking the operation)', async () => {
    const { showcase, ...withoutShowcase } = hubPayload;
    stubApiFetch([{ url: DOCS_LINK_URL, method: 'GET', body: withoutShowcase }]);

    const result = await makeRepository().hub();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.showcase).toBeUndefined();
    }
  });

  it('guards a 500 envelope into a Failed Result', async () => {
    stubApiFetch([
      {
        url: DOCS_LINK_URL,
        method: 'GET',
        status: 500,
        body: {
          error: { code: 'internal', message: 'Unexpected failure.', requestId: 'req-500' },
        },
      },
    ]);

    const result = await makeRepository().hub();

    expect(result).toEqual(
      failed(
        new ServerFailure('Unexpected failure.', {
          code: 'internal',
          status: 500,
          requestId: 'req-500',
        }),
      ),
    );
  });

  it('guards a malformed hub body into a Failed Result (invalid_response)', async () => {
    stubApiFetch([{ url: DOCS_LINK_URL, method: 'GET', body: { pathCount: 'many' } }]);

    const result = await makeRepository().hub();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().hub();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
