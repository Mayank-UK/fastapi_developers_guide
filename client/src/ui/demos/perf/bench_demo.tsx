import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetPerfBenchDemoUseCase } from '../../../domain/demo/get-perf-bench-demo-usecase';
import type {
  CompressionRow,
  HealthAfter,
  HygieneRow,
  PerfBenchPanel,
  PerfFactRow,
} from '../../../domain/demo/perf-bench';

/**
 * PerfBenchDemo — the performance topic's live bench (demo block id
 * `perf:bench`). One read where the server measures, on the very request
 * that serves it: real gzip over the bytes of two payloads this API
 * serves (the topic index and this page's own detail, at level 1 — the
 * nginx edge's live default — and level 6), the on-loop vs threadpool
 * hygiene comparison with a concurrent real /api/health and a loop-lag
 * probe witnessing each, uvicorn's auto-selected loop and HTTP parser
 * introspected from the serving process, the engine pool's counters, and
 * the stdlib GC read plus one measured off-loop collection. The last row
 * is the receipt: a real /api/health after the whole bench.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: PerfBenchPanel };

function CompressionItem({ row }: { row: CompressionRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`pbf-c-${row.payloadId}-${row.level}`}>
      <span className="text-on-surface-variant">level {row.level}:</span> {row.rawBytes} →{' '}
      {row.gzippedBytes} bytes <span className="text-primary">({row.savedPercent}% saved)</span>{' '}
      <span className="text-on-surface-variant">
        enc {row.encodeMs}ms · dec {row.decodeMs}ms
      </span>
    </p>
  );
}

function HygieneItem({ row }: { row: HygieneRow }) {
  const tone = row.label === 'on-loop-block' ? 'text-error' : 'text-primary';
  return (
    <section
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      data-testid={`pbf-h-${row.label}`}
    >
      <p className={`font-mono text-caption ${tone}`}>
        {row.label} — elapsed {row.elapsedMs}ms · loop lag max {row.loopLagMaxMs}ms · health{' '}
        {row.concurrentHealthMs}ms ({row.concurrentHealthStatus})
      </p>
      <p className="text-caption text-on-surface-variant">{row.verdict}</p>
    </section>
  );
}

function FactItem({ row }: { row: PerfFactRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`pbf-f-${row.id}`}>
      <span className="text-on-surface-variant">{row.label}:</span> {row.value}
    </p>
  );
}

function Receipt({ health }: { health: HealthAfter }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid="pbf-receipt">
      health after the bench: {health.status} in {health.elapsedMs}ms — the loop never wedged
    </p>
  );
}

export default function PerfBenchDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetPerfBenchDemoUseCase = container.getPerfBenchDemoUseCase;
    const result: Result<PerfBenchPanel> = await useCase.panel();
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
    return <p data-testid="pbf-loading">Running the bench…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the performance bench"
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
    <section className="flex flex-col gap-sm" data-testid="pbf-panel">
      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="pbf-compression"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Compression</span>{' '}
          <span className="text-on-surface-variant">
            real payloads, real gzip — {data.compression[0]?.payload}
          </span>
        </p>
        {data.compression.map((row) => (
          <CompressionItem key={`${row.payloadId}-${row.level}`} row={row} />
        ))}
      </section>

      <section className="flex flex-col gap-xxs" data-testid="pbf-hygiene">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Async hygiene</span>{' '}
          <span className="text-on-surface-variant">
            the same 80ms CPU block, contained vs on the loop
          </span>
        </p>
        {data.hygiene.map((row) => (
          <HygieneItem key={row.label} row={row} />
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="pbf-loop"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Loop + protocol</span>{' '}
          <span className="text-on-surface-variant">introspected, never assumed</span>
        </p>
        {data.loop.map((row) => (
          <FactItem key={row.id} row={row} />
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="pbf-pool"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Engine pool</span>{' '}
          <span className="text-on-surface-variant">the composition root's counters, live</span>
        </p>
        {data.pool.map((row) => (
          <FactItem key={row.id} row={row} />
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="pbf-gc"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">GC</span>{' '}
          <span className="text-on-surface-variant">the stdlib collector, read and timed</span>
        </p>
        {data.gcFacts.map((row) => (
          <FactItem key={row.id} row={row} />
        ))}
        <p className="font-mono text-caption text-on-surface" data-testid="pbf-gc-collect">
          {data.gcCollection.workload}: {data.gcCollection.elapsedMs}ms,{' '}
          {data.gcCollection.collected} objects
          {data.gcCollection.offLoop ? ' (off-loop via to_thread)' : ''}
        </p>
      </section>

      <Receipt health={data.healthAfter} />

      <p className="text-caption text-on-surface-variant" data-testid="pbf-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
