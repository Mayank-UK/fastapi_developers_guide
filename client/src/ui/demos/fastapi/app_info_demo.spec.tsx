import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { FastApiAppInfoDemo } from './app_info_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetFastApiAppInfoDemoUseCase } from '../../../domain/demo/get-fastapi-app-info-demo-usecase';
import type { FastApiAppInfoData } from '../../../domain/demo/fastapi-app-info';

/**
 * FastApiAppInfoDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container (the token-swap seam), so the
 * spec substitutes fakes instead of stubbing fetch. Behavior, not
 * implementation: the app's facts render (identity, docs links opening a
 * new tab, the stack, the wiring), the route table groups by router prefix,
 * and failures degrade to the shared error panel with recovery.
 */

const fixture: FastApiAppInfoData = {
  title: 'FastAPI Developers Guide',
  version: '0.1.0',
  environment: 'dev',
  docs: { docsUrl: '/docs', redocUrl: '/redoc', openapiUrl: '/openapi.json' },
  stack: { fastapi: '0.143.1', starlette: '1.8.0', pydantic: '2.14.1' },
  middleware: ['RequestIdMiddleware'],
  exceptionHandlers: [
    { exception: 'AppError', handler: 'handle_app_error' },
    { exception: 'Exception', handler: 'handle_unexpected_error' },
  ],
  routes: [
    { path: '/api/content', methods: ['GET'], tags: ['content'] },
    { path: '/api/content/{topicId}', methods: ['GET'], tags: ['content'] },
    { path: '/api/demo/fastapi/app-info', methods: ['GET'], tags: ['demo:fastapi'] },
    { path: '/api/health', methods: ['GET'], tags: ['health'] },
  ],
};

function stubUseCase(execute: () => Promise<Result<FastApiAppInfoData>>): void {
  container.initialize(createAppConfig());
  container.register(
    ContainerTokens.GetFastApiAppInfoDemoUseCase,
    { execute } as unknown as GetFastApiAppInfoDemoUseCase,
  );
}

describe('FastApiAppInfoDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['fastapi:app-info']).toBeDefined();
  });

  it('renders loading first, then the app facts and the grouped route table', async () => {
    stubUseCase(async () => success(fixture));

    render(<FastApiAppInfoDemo />);

    expect(screen.getByTestId('fastapi-app-info-loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByTestId('fai-routes')).toBeInTheDocument());

    // Identity and environment.
    expect(screen.getByTestId('fai-facts')).toHaveTextContent('FastAPI Developers Guide');
    expect(screen.getByTestId('fai-facts')).toHaveTextContent('env: dev');

    // Docs links open in a new tab, pointing at the reported mounts.
    const swagger = screen.getByTestId('fai-docs-swagger');
    expect(swagger).toHaveAttribute('href', '/docs');
    expect(swagger).toHaveAttribute('target', '_blank');
    expect(screen.getByTestId('fai-docs-redoc')).toHaveAttribute('href', '/redoc');
    expect(screen.getByTestId('fai-docs-openapi')).toHaveAttribute('href', '/openapi.json');

    // The stack and the wiring render.
    expect(screen.getByTestId('fai-stack')).toHaveTextContent('starlette 1.8.0');
    expect(screen.getByTestId('fai-wiring')).toHaveTextContent('RequestIdMiddleware');
    expect(screen.getByTestId('fai-wiring')).toHaveTextContent('AppError → handle_app_error');

    // Route table: grouped by router prefix, methods and tags per row.
    const groups = screen.getAllByTestId('fai-route-group');
    expect(groups).toHaveLength(3); // /api (first), /api/content, /api/demo/fastapi
    expect(groups[0]).toHaveTextContent('/api/health');
    expect(groups[1]).toHaveTextContent('/api/content/{topicId}');
    expect(groups[2]).toHaveTextContent('demo:fastapi');
    expect(screen.getByTestId('fai-routes')).toHaveTextContent('4 paths');
    expect(screen.getByTestId('fai-routes')).toHaveTextContent('GET');
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The demo endpoint is down.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-34',
            }),
          )
        : success(fixture);
    });

    render(<FastApiAppInfoDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-runs the use case and the payload renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('fai-routes')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
