import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DocsLinkDemo } from './docs_link_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDocsLinkDemoUseCase } from '../../../domain/demo/get-docs-link-demo-usecase';
import type { DocsHub } from '../../../domain/demo/docs-link';

/**
 * DocsLinkDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the
 * token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * hub's links open the real docs mounts in a new tab, the counts and
 * areas render, the posts operations table carries the generated
 * operationIds and documented responses, the showcase slice names the
 * $ref chain (PostCreate in, Post and HTTPValidationError out), and
 * failures degrade to the shared error panel with recovery.
 */

const fixture: DocsHub = {
  infoTitle: 'FastAPI Developers Guide',
  infoVersion: '0.1.0',
  openapiVersion: '3.1.0',
  docs: { swaggerUi: '/docs', redoc: '/redoc', openapiJson: '/openapi.json' },
  pathCount: 25,
  operationCount: 34,
  areaCount: 3,
  areas: [
    { tag: 'content', paths: 2, operations: 2, methods: ['GET'] },
    { tag: 'demo:api', paths: 3, operations: 3, methods: ['GET', 'POST'] },
    { tag: 'posts', paths: 2, operations: 4, methods: ['GET', 'POST', 'PUT'] },
  ],
  schemaCount: 93,
  schemaNames: ['HTTPValidationError', 'Post', 'PostCreate', 'PostPage'],
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
  reasoning: 'Every fact here was read from the same OpenAPI document.',
};

function stubUseCase(hub: () => Promise<Result<DocsHub>>): void {
  container.initialize(createAppConfig());
  container.register(
    ContainerTokens.GetDocsLinkDemoUseCase,
    { hub } as unknown as GetDocsLinkDemoUseCase,
  );
}

describe('DocsLinkDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['api:docs-link']).toBeDefined();
  });

  it('renders loading first, then the hub: links, counts, areas, operations, showcase', async () => {
    stubUseCase(async () => success(fixture));

    render(<DocsLinkDemo />);

    expect(screen.getByTestId('dl-loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByTestId('dl-links')).toBeInTheDocument());

    // The docs links open in a new tab, pointing at the reported mounts.
    const swagger = screen.getByTestId('dl-link-swagger');
    expect(swagger).toHaveAttribute('href', '/docs');
    expect(swagger).toHaveAttribute('target', '_blank');
    expect(screen.getByTestId('dl-link-redoc')).toHaveAttribute('href', '/redoc');
    expect(screen.getByTestId('dl-link-openapi')).toHaveAttribute('href', '/openapi.json');

    // Identity and the schema's own numbers.
    expect(screen.getByTestId('dl-facts')).toHaveTextContent('FastAPI Developers Guide');
    expect(screen.getByTestId('dl-facts')).toHaveTextContent('OpenAPI 3.1.0');
    expect(screen.getByTestId('dl-facts')).toHaveTextContent('25 paths');
    expect(screen.getByTestId('dl-facts')).toHaveTextContent('34 operations');
    expect(screen.getByTestId('dl-facts')).toHaveTextContent('93 schemas');

    // Areas with methods, including the posts one.
    expect(screen.getAllByTestId('dl-area')).toHaveLength(3);
    expect(screen.getByTestId('dl-areas')).toHaveTextContent('posts');
    expect(screen.getByTestId('dl-areas')).toHaveTextContent('GET POST PUT');

    // The posts operations with generated ids and documented responses.
    const rows = screen.getAllByTestId('dl-posts-row');
    expect(rows).toHaveLength(2);
    expect(screen.getByTestId('dl-posts')).toHaveTextContent('create_post_api_posts_post');
    expect(screen.getByTestId('dl-posts')).toHaveTextContent('201 · 422');

    // The showcase slice names the $ref chain.
    const showcase = screen.getByTestId('dl-showcase');
    expect(showcase).toHaveTextContent('POST /api/posts');
    expect(showcase).toHaveTextContent('request → PostCreate');
    expect(showcase).toHaveTextContent('201 → Post');
    expect(showcase).toHaveTextContent('422 → HTTPValidationError');

    expect(screen.getByTestId('dl-reasoning')).toHaveTextContent('Every fact here was read');
  });

  it('renders the hub without a showcase slice honestly', async () => {
    const { showcase, ...withoutShowcase } = fixture;
    stubUseCase(async () => success({ ...withoutShowcase, showcase: undefined }));

    render(<DocsLinkDemo />);

    await waitFor(() => expect(screen.getByTestId('dl-links')).toBeInTheDocument());
    expect(screen.queryByTestId('dl-showcase')).not.toBeInTheDocument();
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The hub endpoint is down.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-77',
            }),
          )
        : success(fixture);
    });

    render(<DocsLinkDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-runs the use case and the hub renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('dl-links')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
