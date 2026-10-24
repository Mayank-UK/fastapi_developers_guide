import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetObsViewerDemoUseCase } from '../../../domain/demo/get-obs-viewer-demo-usecase';
import type { LogViewerPanel } from '../../../domain/demo/obs-viewer';

/**
 * ObsViewerDemo — the observability topic's structured-log viewer (demo
 * block id `obs:viewer`). One live read of the server's REAL structlog
 * pipeline: the active processor chain introspected from the process's
 * own configuration (each stage with its role), the configured log level
 * with its real source, and the recent-events ring — every row a real
 * logged event with its level, event name, correlation request id, and
 * rendered field pairs. The panel's own request id is surfaced so the
 * reader can match it against this very response's x-request-id header
 * and against the obs_viewer rows the request itself logged.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: LogViewerPanel };

function levelTone(level: string): string {
  if (level === 'warning') return 'text-warning';
  if (level === 'error' || level === 'critical') return 'text-error';
  if (level === 'debug') return 'text-on-surface-variant';
  return 'text-on-surface';
}

export default function ObsViewerDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetObsViewerDemoUseCase = container.getObsViewerDemoUseCase;
    const result: Result<LogViewerPanel> = await useCase.panel();
    if (result.ok) {
      setPanel({ state: 'ready', data: result.value });
    } else {
      setPanel({ state: 'failed', failure: result.failure });
    }
  }, []);

  useEffect(() => {
    void loadPanel();
  }, [loadPanel]);

  if (panel.state === 'loading') {
    return <p data-testid="ov-loading">Reading the live pipeline and recent events…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the structured-log viewer"
        failure={panel.failure}
        onRetry={() => {
          setPanel({ state: 'loading' });
          void loadPanel();
        }}
      />
    );
  }

  const data = panel.data;
  const events = [...data.events].reverse();

  return (
    <section className="flex flex-col gap-sm" data-testid="ov-panel">
      <header className="flex flex-wrap items-baseline gap-x-sm gap-y-xxs">
        <p className="font-mono text-caption text-on-surface" data-testid="ov-level">
          level {data.configuredLevel} · {data.levelSource}
        </p>
        <p className="font-mono text-caption text-on-surface-variant" data-testid="ov-ring">
          ring {data.ringCapacity} events · held {data.events.length}
        </p>
        <p className="font-mono text-caption text-primary" data-testid="ov-panel-request-id">
          this panel's request id: {data.panelRequestId}
        </p>
      </header>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="ov-pipeline"
      >
        {data.pipeline.map((stage) => (
          <p
            key={stage.processor}
            data-testid={`ov-stage-${stage.processor}`}
            className="font-mono text-caption text-on-surface"
          >
            {stage.orderIndex} · <span className="text-primary">{stage.processor}</span> —{' '}
            {stage.role}
          </p>
        ))}
        <p className="text-caption text-on-surface-variant" data-testid="ov-pipeline-note">
          {data.pipelineNote}
        </p>
      </section>

      <section className="flex flex-col gap-xxs" data-testid="ov-events">
        {events.map((event) => (
          <div
            key={event.sequence}
            data-testid={`ov-event-${event.sequence}`}
            className="flex flex-wrap items-baseline gap-x-sm font-mono text-caption"
          >
            <span className={`font-semibold ${levelTone(event.level)}`}>[{event.level}]</span>
            <span className={event.requestId === data.panelRequestId ? 'text-primary' : 'text-on-surface'}>
              {event.event}
            </span>
            {event.requestId !== '' && (
              <span className="text-on-surface-variant">id={event.requestId}</span>
            )}
            {event.fields.map((field) => (
              <span key={field.name} className="text-on-surface-variant">
                {field.name}={field.value}
              </span>
            ))}
          </div>
        ))}
      </section>

      <p className="text-caption text-on-surface-variant" data-testid="ov-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
