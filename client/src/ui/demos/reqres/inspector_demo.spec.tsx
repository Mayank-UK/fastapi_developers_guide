import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RequestInspectorDemo } from './inspector_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetReqresInspectorDemoUseCase } from '../../../domain/demo/get-reqres-inspector-demo-usecase';
import type {
  InspectorProbe,
  RequestInspectorData,
} from '../../../domain/demo/reqres-inspector';

/**
 * RequestInspectorDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec swaps
 * the token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the form
 * fires the probe as configured (query, custom header, POST body), the
 * reflection renders the request line with repeated query values and the
 * parsed body facts, switching to POST reveals the body field, and
 * failures degrade to the shared error panel with recovery.
 */

const reflectedFixture: RequestInspectorData = {
  method: 'GET',
  path: '/api/demo/reqres/inspector',
  rawQuery: 'tag=a&tag=b&zoom=2',
  queryParams: [
    { name: 'tag', values: ['a', 'b'], isRepeated: true },
    { name: 'zoom', values: ['2'], isRepeated: false },
  ],
  headers: [
    { name: 'accept', value: 'application/json' },
    { name: 'x-probe', value: 'hello' },
  ],
  requestId: 'req-inspect-1',
  requestIdHeader: 'x-request-id',
  reasoning: 'This payload is the handler\'s own view of the GET request that fetched it.',
};

const postFixture: RequestInspectorData = {
  method: 'POST',
  path: '/api/demo/reqres/inspector',
  queryParams: [],
  headers: [{ name: 'content-type', value: 'application/json' }],
  contentType: 'application/json',
  contentLength: 21,
  bodyMessage: 'a body the server will parse',
  client: { host: '127.0.0.1', port: 51000 },
  requestId: 'req-inspect-2',
  requestIdHeader: 'x-request-id',
  reasoning: 'The POST variant: the body contract is visible.',
};

/** Capture the probe the component fired, answering with a fixture. */
function stubUseCase(
  respond: (probe: InspectorProbe) => Result<RequestInspectorData>,
): InspectorProbe[] {
  const fired: InspectorProbe[] = [];
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetReqresInspectorDemoUseCase, {
    execute: (probe: InspectorProbe) => {
      fired.push(probe);
      return Promise.resolve(respond(probe));
    },
  } as unknown as GetReqresInspectorDemoUseCase);
  return fired;
}

describe('RequestInspectorDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['reqres:inspector']).toBeDefined();
  });

  it('sends the configured probe and renders the reflected view', async () => {
    const fired = stubUseCase(() => success(reflectedFixture));

    render(<RequestInspectorDemo />);

    expect(screen.getByTestId('ri-idle')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('ri-send'));

    await waitFor(() => expect(screen.getByTestId('ri-result')).toBeInTheDocument());
    expect(fired).toEqual([
      {
        method: 'GET',
        query: 'tag=a&tag=b&zoom=2',
        headerName: 'x-probe',
        headerValue: 'hello',
      },
    ]);

    expect(screen.getByTestId('ri-request-line')).toHaveTextContent('GET');
    expect(screen.getByTestId('ri-request-line')).toHaveTextContent('?tag=a&tag=b&zoom=2');
    expect(screen.getByTestId('ri-query-params')).toHaveTextContent('tag');
    expect(screen.getByTestId('ri-query-params')).toHaveTextContent('[a, b]');
    expect(screen.getByTestId('ri-query-params')).toHaveTextContent('repeated — 2 values');
    expect(screen.getByTestId('ri-headers')).toHaveTextContent('x-probe');
    expect(screen.getByTestId('ri-headers')).toHaveTextContent('hello');
    expect(screen.getByTestId('ri-request-id')).toHaveTextContent('req-inspect-1');
    expect(screen.getByTestId('ri-reasoning')).toHaveTextContent("handler's own view");
  });

  it('switches to POST, reveals the body field, and reports the body facts', async () => {
    const fired = stubUseCase(() => success(postFixture));

    render(<RequestInspectorDemo />);

    expect(screen.queryByTestId('ri-body')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('ri-method-post'));
    expect(screen.getByTestId('ri-body')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('ri-send'));

    await waitFor(() => expect(screen.getByTestId('ri-result')).toBeInTheDocument());
    expect(fired).toHaveLength(1);
    expect(fired[0]?.method).toBe('POST');
    expect(fired[0]?.bodyMessage).toBe('a body the server will parse');
    expect(screen.getByTestId('ri-body-facts')).toHaveTextContent('content-type: application/json');
    expect(screen.getByTestId('ri-body-facts')).toHaveTextContent('content-length: 21');
    expect(screen.getByTestId('ri-body-facts')).toHaveTextContent('a body the server will parse');
    expect(screen.getByTestId('ri-client')).toHaveTextContent('127.0.0.1:51000');
  });

  it('omits the custom header when its name is cleared', async () => {
    const fired = stubUseCase(() => success(reflectedFixture));

    render(<RequestInspectorDemo />);

    fireEvent.change(screen.getByTestId('ri-header-name'), { target: { value: '' } });
    fireEvent.click(screen.getByTestId('ri-send'));

    await waitFor(() => expect(screen.getByTestId('ri-result')).toBeInTheDocument());
    expect(fired[0]).toEqual({ method: 'GET', query: 'tag=a&tag=b&zoom=2' });
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('Request validation failed.', {
              code: 'validation_failed',
              status: 422,
              requestId: 'req-99',
            }),
          )
        : success(reflectedFixture);
    });

    render(<RequestInspectorDemo />);

    fireEvent.click(screen.getByTestId('ri-send'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('validation_failed');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('ri-result')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
