import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import ObsViewerDemo from './viewer_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetObsViewerDemoUseCase } from '../../../domain/demo/get-obs-viewer-demo-usecase';
import type { LogViewerPanel } from '../../../domain/demo/obs-viewer';

/**
 * ObsViewerDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the panel
 * renders the introspected pipeline stages in execution order, the
 * configured level beside its source, and the ring's real events newest
 * first with level, event name, request id, and field pairs; the panel's
 * own request id is surfaced; a failed round degrades to the shared error
 * panel with recovery.
 */

const fakePanel: LogViewerPanel = {
  configuredLevel: 'info',
  levelSource: 'FDG_LOG_LEVEL env → AppConfig.log_level (default: info)',
  ringCapacity: 50,
  pipeline: [
    {
      orderIndex: 0,
      processor: 'merge_contextvars',
      role: 'merges the request-scoped bound context into every event',
    },
    { orderIndex: 1, processor: 'JSONRenderer', role: 'renders one JSON object per line' },
  ],
  events: [
    {
      sequence: 39,
      level: 'info',
      event: 'db_migrations_skipped',
      requestId: '',
      timestamp: '2026-10-24T06:59:00Z',
      fields: [{ name: 'reason', value: 'postgresql unreachable' }],
    },
    {
      sequence: 40,
      level: 'info',
      event: 'http_request',
      requestId: 'some-earlier-request',
      timestamp: '2026-10-24T07:00:00Z',
      fields: [
        { name: 'method', value: 'GET' },
        { name: 'path', value: '/api/health' },
        { name: 'status', value: '200' },
      ],
    },
    {
      sequence: 41,
      level: 'warning',
      event: 'app_error',
      requestId: 'some-earlier-request',
      timestamp: '2026-10-24T07:00:01Z',
      fields: [{ name: 'kind', value: 'not_found' }],
    },
    {
      sequence: 42,
      level: 'info',
      event: 'obs_viewer_panel_opened',
      requestId: 'the-panels-own-id',
      timestamp: '2026-10-24T07:00:02Z',
      fields: [{ name: 'panel', value: 'obs:viewer' }],
    },
  ],
  panelRequestId: 'the-panels-own-id',
  pipelineNote: 'The active pipeline, introspected live.',
  honestyNote: 'Every row was really logged by this process.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<LogViewerPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetObsViewerDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetObsViewerDemoUseCase);
}

describe('ObsViewerDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['obs:viewer']).toBeDefined();
  });

  it('renders the pipeline, level, and the ring events newest first', async () => {
    stubUseCase(() => success(fakePanel));

    render(<ObsViewerDemo />);

    await waitFor(() => expect(screen.getByTestId('ov-panel')).toBeInTheDocument());
    expect(screen.getByTestId('ov-level')).toHaveTextContent('level info');
    expect(screen.getByTestId('ov-level')).toHaveTextContent('FDG_LOG_LEVEL');
    expect(screen.getByTestId('ov-ring')).toHaveTextContent('ring 50 events');
    expect(screen.getByTestId('ov-panel-request-id')).toHaveTextContent('the-panels-own-id');
    expect(screen.getByTestId('ov-stage-merge_contextvars')).toHaveTextContent(
      'merges the request-scoped bound context',
    );
    expect(screen.getByTestId('ov-stage-JSONRenderer')).toHaveTextContent(
      'one JSON object per line',
    );
    expect(screen.getByTestId('ov-event-42')).toHaveTextContent('[info]');
    expect(screen.getByTestId('ov-event-42')).toHaveTextContent('obs_viewer_panel_opened');
    expect(screen.getByTestId('ov-event-42')).toHaveTextContent('id=the-panels-own-id');
    expect(screen.getByTestId('ov-event-41')).toHaveTextContent('[warning]');
    expect(screen.getByTestId('ov-event-41')).toHaveTextContent('kind=not_found');
    // An event logged outside any request carries an empty id — rendered
    // without the id= prefix (present-but-empty is DATA on this wire).
    expect(screen.getByTestId('ov-event-39')).toHaveTextContent('db_migrations_skipped');
    expect(screen.getByTestId('ov-event-39')).not.toHaveTextContent('id=');
    // Newest first: the newest sequence appears before the older ones.
    const events = screen.getByTestId('ov-events');
    expect(events.textContent?.indexOf('obs_viewer_panel_opened')).toBeLessThan(
      events.textContent?.indexOf('http_request') ?? -1,
    );
    expect(screen.getByTestId('ov-honesty-note')).toHaveTextContent('really logged');
  });

  it('degrades a failed round to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The viewer did not answer.', {
              code: 'internal',
              status: 500,
              requestId: 'req-obs-1',
            }),
          )
        : success(fakePanel);
    });

    render(<ObsViewerDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('internal');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('ov-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
