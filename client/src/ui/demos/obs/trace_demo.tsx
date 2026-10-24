import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetObsTraceDemoUseCase } from '../../../domain/demo/get-obs-trace-demo-usecase';
import type { TraceFanout, TraceRound } from '../../../domain/demo/obs-trace';

/**
 * ObsTraceDemo — the observability topic's trace fan-out (demo block id
 * `obs:trace`). One live read where the server drove three REAL internal
 * requests through the running app — a clean 200, the posts resource's
 * 404, FastAPI's 422 — each carrying an inbound request id derived from
 * the panel request's own id (the trace root). Each round shows the
 * correlated evidence: the echoed header, the error envelope's requestId
 * on failed rounds, and the log rows the round really produced — the
 * access-log line plus the failure line, one id tying them together.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: TraceFanout };

function statusTone(round: TraceRound): string {
  if (round.status >= 500) return 'text-error';
  if (round.status >= 400) return 'text-warning';
  return 'text-primary';
}

function Round({ round }: { round: TraceRound }) {
  return (
    <section
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      data-testid={`ot-round-${round.label}`}
    >
      <p className="font-mono text-caption text-on-surface">
        <span className="text-on-surface-variant">{round.requestLine}</span>{' '}
        <span className={statusTone(round)}>→ {round.status}</span>{' '}
        <span className="text-on-surface-variant">
          {round.firstByteMs}ms first byte · {round.durationMs}ms total
        </span>
      </p>
      <p className="font-mono text-caption text-on-surface-variant" data-testid={`ot-id-${round.label}`}>
        id {round.inboundRequestId} · header echoed: {round.headerEchoed ? 'yes' : 'NO'}
        {round.envelopeCode !== null && ` · envelope ${round.envelopeCode} · requestId ${
          round.envelopeRequestId ?? '—'
        }`}
      </p>
      <div className="flex flex-col gap-xxs" data-testid={`ot-logs-${round.label}`}>
        {round.logEvents.map((event) => (
          <p key={event.sequence} className="font-mono text-caption text-on-surface">
            <span className="text-on-surface-variant">[{event.level}]</span> {event.event}{' '}
            <span className="text-on-surface-variant">
              {event.fields.map((field) => `${field.name}=${field.value}`).join(' ')}
            </span>
          </p>
        ))}
      </div>
      <p className="text-caption text-on-surface-variant">{round.note}</p>
    </section>
  );
}

export default function ObsTraceDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetObsTraceDemoUseCase = container.getObsTraceDemoUseCase;
    const result: Result<TraceFanout> = await useCase.fanout();
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
    return <p data-testid="ot-loading">Driving three real rounds through the app…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the trace fan-out"
        failure={panel.failure}
        onRetry={() => {
          setPanel({ state: 'loading' });
          void loadPanel();
        }}
      />
    );
  }

  const data = panel.data;

  return (
    <section className="flex flex-col gap-sm" data-testid="ot-panel">
      <header className="flex flex-wrap items-baseline gap-x-sm gap-y-xxs">
        <p className="font-mono text-caption text-primary" data-testid="ot-root">
          trace root {data.rootRequestId}
        </p>
      </header>

      {data.rounds.map((round) => (
        <Round key={round.label} round={round} />
      ))}

      <p className="text-caption text-on-surface" data-testid="ot-correlation-note">
        {data.correlationNote}
      </p>
      <p className="text-caption text-on-surface-variant" data-testid="ot-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
