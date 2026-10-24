import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ObsTraceDemo from './trace_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetObsTraceDemoUseCase } from '../../../domain/demo/get-obs-trace-demo-usecase';
import type { TraceFanout } from '../../../domain/demo/obs-trace';

/**
 * ObsTraceDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the panel
 * renders the trace root, the three real rounds with their statuses,
 * derived ids, envelope facts, and correlated log rows, plus the
 * correlation and honesty notes; a failed round degrades to the shared
 * error panel with recovery.
 */

const fakeFanout: TraceFanout = {
  rootRequestId: 'trace-root-id-123',
  derivedIdConvention:
    "child ids are '<root-prefix>-<label>': the shared prefix is this panel's own request id.",
  rounds: [
    {
      label: 'ok',
      requestLine: 'GET /api/health',
      inboundRequestId: 'trace-root-id-123-ok',
      status: 200,
      firstByteMs: 0.4,
      durationMs: 0.9,
      headerEchoed: true,
      envelopeCode: null,
      envelopeRequestId: null,
      logEvents: [
        {
          sequence: 10,
          level: 'info',
          event: 'http_request',
          requestId: 'trace-root-id-123-ok',
          timestamp: '2026-10-24T07:00:00Z',
          fields: [{ name: 'status', value: '200' }],
        },
      ],
      note: 'A healthy round leaves exactly one row — the access-log line.',
    },
    {
      label: 'not-found',
      requestLine: 'GET /api/posts/nope',
      inboundRequestId: 'trace-root-id-123-not-found',
      status: 404,
      firstByteMs: 0.5,
      durationMs: 1.1,
      headerEchoed: true,
      envelopeCode: 'not_found',
      envelopeRequestId: 'trace-root-id-123-not-found',
      logEvents: [
        {
          sequence: 11,
          level: 'warning',
          event: 'app_error',
          requestId: 'trace-root-id-123-not-found',
          timestamp: '2026-10-24T07:00:01Z',
          fields: [{ name: 'kind', value: 'not_found' }],
        },
        {
          sequence: 12,
          level: 'info',
          event: 'http_request',
          requestId: 'trace-root-id-123-not-found',
          timestamp: '2026-10-24T07:00:01Z',
          fields: [{ name: 'status', value: '404' }],
        },
      ],
      note: 'One id, three correlations: header, envelope, and log rows.',
    },
    {
      label: 'validation',
      requestLine: 'GET /api/posts?page=notanumber',
      inboundRequestId: 'trace-root-id-123-validation',
      status: 422,
      firstByteMs: 0.6,
      durationMs: 1.0,
      headerEchoed: true,
      envelopeCode: 'validation_failed',
      envelopeRequestId: 'trace-root-id-123-validation',
      logEvents: [
        {
          sequence: 13,
          level: 'info',
          event: 'request_validation_failed',
          requestId: 'trace-root-id-123-validation',
          timestamp: '2026-10-24T07:00:02Z',
          fields: [{ name: 'detail_count', value: '1' }],
        },
      ],
      note: 'One id, three correlations: header, envelope, and log rows.',
    },
  ],
  correlationNote: 'Three places, one id — that is what correlation means.',
  honestyNote: 'OpenTelemetry is NOT a dependency here — the request-id mechanism is real.',
};

/** Swap the container's use-case token for a stub answering the fan-out. */
function stubUseCase(respond: () => Result<TraceFanout>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetObsTraceDemoUseCase, {
    fanout: () => Promise.resolve(respond()),
  } as unknown as GetObsTraceDemoUseCase);
}

describe('ObsTraceDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['obs:trace']).toBeDefined();
  });

  it('renders the root and the three rounds with correlated evidence', async () => {
    stubUseCase(() => success(fakeFanout));

    render(<ObsTraceDemo />);

    await waitFor(() => expect(screen.getByTestId('ot-panel')).toBeInTheDocument());
    expect(screen.getByTestId('ot-root')).toHaveTextContent('trace-root-id-123');

    const ok = screen.getByTestId('ot-round-ok');
    expect(ok).toHaveTextContent('GET /api/health → 200');
    expect(screen.getByTestId('ot-id-ok')).toHaveTextContent('header echoed: yes');
    expect(screen.getByTestId('ot-logs-ok')).toHaveTextContent('http_request');

    const notFound = screen.getByTestId('ot-round-not-found');
    expect(notFound).toHaveTextContent('→ 404');
    expect(screen.getByTestId('ot-id-not-found')).toHaveTextContent('envelope not_found');
    expect(screen.getByTestId('ot-id-not-found')).toHaveTextContent(
      'requestId trace-root-id-123-not-found',
    );
    expect(screen.getByTestId('ot-logs-not-found')).toHaveTextContent('app_error');
    expect(screen.getByTestId('ot-logs-not-found')).toHaveTextContent('kind=not_found');

    const validation = screen.getByTestId('ot-round-validation');
    expect(validation).toHaveTextContent('→ 422');
    expect(screen.getByTestId('ot-logs-validation')).toHaveTextContent(
      'request_validation_failed',
    );

    expect(screen.getByTestId('ot-correlation-note')).toHaveTextContent('Three places, one id');
    expect(screen.getByTestId('ot-honesty-note')).toHaveTextContent('NOT a dependency');
  });

  it('degrades a failed round to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The fan-out did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-obs-trace-1',
            }),
          )
        : success(fakeFanout);
    });

    render(<ObsTraceDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('ot-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
