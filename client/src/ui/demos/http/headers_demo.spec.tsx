import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { HttpHeadersDemo } from './headers_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetHttpHeadersDemoUseCase } from '../../../domain/demo/get-http-headers-demo-usecase';
import type {
  HttpHeadersDemoRequest,
  HttpHeadersEchoData,
} from '../../../domain/demo/http-headers';

/**
 * HttpHeadersDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the form fires
 * the request as configured, the echo renders with per-header scope
 * classification, an invalid header name is refused client-side, and
 * failures degrade to the shared error panel with recovery.
 */

const fixture: HttpHeadersEchoData = {
  method: 'GET',
  path: '/api/demo/http/headers',
  query: 'from=client-demo',
  headers: [
    {
      name: 'user-agent',
      value: 'Mozilla/5.0 (vitest)',
      scope: 'end-to-end',
      note: 'identifies the calling software; log it, rarely branch on it',
    },
    { name: 'x-demo-trace', value: 'hello-http', scope: 'end-to-end' },
    { name: 'connection', value: 'keep-alive', scope: 'hop-by-hop' },
  ],
  hopByHop: [
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
  ],
};

const postFixture: HttpHeadersEchoData = {
  ...fixture,
  method: 'POST',
  contentType: 'application/json',
  bodyMessage: 'hello from the browser',
  headers: [
    { name: 'content-type', value: 'application/json', scope: 'end-to-end' },
    ...fixture.headers,
  ],
};

/** Capture the request the component fired, answering with the fixture. */
function stubUseCase(
  respond: (request: HttpHeadersDemoRequest) => Result<HttpHeadersEchoData>,
): HttpHeadersDemoRequest[] {
  const fired: HttpHeadersDemoRequest[] = [];
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetHttpHeadersDemoUseCase, {
    execute: (request: HttpHeadersDemoRequest) => {
      fired.push(request);
      return Promise.resolve(respond(request));
    },
  } as unknown as GetHttpHeadersDemoUseCase);
  return fired;
}

describe('HttpHeadersDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['http:headers']).toBeDefined();
  });

  it('starts idle and fires a GET with the custom header when sent', async () => {
    const fired = stubUseCase(() => success(fixture));

    render(<HttpHeadersDemo />);

    expect(screen.getByTestId('hh-idle')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('hh-value'), { target: { value: 'hello-http' } });
    fireEvent.click(screen.getByTestId('hh-send'));

    await waitFor(() => expect(screen.getByTestId('hh-echo')).toBeInTheDocument());
    expect(fired).toEqual([
      { method: 'GET', headerName: 'x-demo-trace', headerValue: 'hello-http' },
    ]);

    // The echo: request line with the raw query, per-header scopes, notes.
    expect(screen.getByTestId('hh-request-line')).toHaveTextContent(
      'GET /api/demo/http/headers?from=client-demo',
    );
    const table = screen.getByTestId('hh-headers');
    expect(table).toHaveTextContent('x-demo-trace');
    expect(table).toHaveTextContent('hello-http');
    expect(table).toHaveTextContent('end-to-end');
    expect(table).toHaveTextContent('hop-by-hop');
    expect(table).toHaveTextContent('identifies the calling software');

    // The reference list rides along.
    expect(screen.getByTestId('hh-hop-by-hop')).toHaveTextContent('transfer-encoding');
  });

  it('switches to POST, sends the body message, and echoes it back', async () => {
    const fired = stubUseCase(() => success(postFixture));

    render(<HttpHeadersDemo />);

    fireEvent.click(screen.getByTestId('hh-method-post'));
    fireEvent.change(screen.getByTestId('hh-message'), {
      target: { value: 'hello from the browser' },
    });
    fireEvent.change(screen.getByTestId('hh-value'), { target: { value: 'hello-http' } });
    fireEvent.click(screen.getByTestId('hh-send'));

    await waitFor(() => expect(screen.getByTestId('hh-echo')).toBeInTheDocument());
    expect(fired).toEqual([
      {
        method: 'POST',
        headerName: 'x-demo-trace',
        headerValue: 'hello-http',
        message: 'hello from the browser',
      },
    ]);
    expect(screen.getByTestId('hh-body')).toHaveTextContent('content-type: application/json');
    expect(screen.getByTestId('hh-body')).toHaveTextContent(
      'body message: “hello from the browser”',
    );
  });

  it('refuses an invalid header name client-side instead of letting fetch throw', () => {
    stubUseCase(() => success(fixture));

    render(<HttpHeadersDemo />);

    fireEvent.change(screen.getByTestId('hh-name'), { target: { value: 'bad header name' } });
    fireEvent.change(screen.getByTestId('hh-value'), { target: { value: 'x' } });

    expect(screen.getByTestId('hh-name-warning')).toBeInTheDocument();
    expect(screen.getByTestId('hh-send')).toBeDisabled();
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The demo endpoint is down.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-77',
            }),
          )
        : success(fixture);
    });

    render(<HttpHeadersDemo />);

    fireEvent.change(screen.getByTestId('hh-value'), { target: { value: 'hello-http' } });
    fireEvent.click(screen.getByTestId('hh-send'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-fires the same request and the echo renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('hh-echo')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
