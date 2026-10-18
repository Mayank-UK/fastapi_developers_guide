import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { MongoConsoleDemo, ConsoleOperationRow } from '../../../domain/demo/mongo-console';

/**
 * MongoConsoleDemo — the mongodb topic's console (demo block id
 * `db:mongo-console`). One payload carries the whole scripted run
 * against the live MongoDB: the idempotent keyed seed, the pydantic
 * refusal (field errors, zero I/O), the insert/find/update/count/
 * delete lifecycle with real outcomes and documents, the index exhibit
 * (COLLSCAN vs IXSCAN over the same query), and a real TTL index
 * definition. Pick a different find tag to re-run — a tag nothing
 * carries answers with an honest empty.
 */

type ConsoleStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: MongoConsoleDemo }
  | { state: 'failed'; failure: Failure };

const TAGS = ['indexes', 'modeling', 'motor', 'demo', 'missing'];

export function DbMongoConsoleDemo() {
  const useCase = container.getMongoConsoleDemoUseCase;
  const [tag, setTag] = useState('indexes');
  const [status, setStatus] = useState<ConsoleStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.run(tag).then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase, tag]);

  const runAgain = () => {
    setStatus({ state: 'loading' });
    void useCase.run(tag).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="mongo-console-loading" className="text-body-sm text-on-surface-variant">
        running the console…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the mongo console" failure={status.failure} onRetry={runAgain} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <div data-testid="mongo-console-tag-picker" className="flex flex-wrap items-center gap-xs">
        <span className="text-caption text-on-surface-variant">find tag:</span>
        {TAGS.map((candidate) => (
          <button
            key={candidate}
            type="button"
            onClick={() => setTag(candidate)}
            className={`rounded-md border px-xs py-xxs font-mono text-caption ${
              candidate === tag
                ? 'border-primary text-primary'
                : 'border-outline text-on-surface-variant hover:text-on-surface'
            }`}
          >
            {candidate}
          </button>
        ))}
      </div>

      <section
        data-testid="mongo-console-seed"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          seed · {data.seed.collection} in {data.database}
        </p>
        <p data-testid="mongo-console-seed-proof" className="font-mono text-caption text-on-surface">
          {data.seed.countBefore} already present · {data.seed.upserted} planted ·{' '}
          {data.seed.totalAfter} total · indexes: {data.seed.indexesEnsured.join(', ')}
        </p>
      </section>

      <section
        data-testid="mongo-console-refusal"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">the boundary refused first</p>
        {data.refusal.errors.map((error) => (
          <p key={error} className="font-mono text-caption text-error">
            {error}
          </p>
        ))}
        <p className="text-caption text-on-surface-variant">
          ConsoleNoteDraft refused the draft before any I/O — MongoDB never saw it.
        </p>
      </section>

      {data.operations.map((operation) => (
        <OperationRun key={operation.op} operation={operation} />
      ))}

      <section
        data-testid="mongo-console-indexes"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          index exhibit · {data.indexShowcase.collection} ({data.indexShowcase.documentCount} docs)
        </p>
        {data.indexShowcase.explains.map((explain) => (
          <p key={explain.label} data-testid="mongo-console-explain" className="font-mono text-caption text-on-surface">
            {explain.label}: <span className={explain.stage === 'IXSCAN' ? 'text-primary' : 'text-error'}>
              {explain.stage}
            </span>{' '}
            · keys={explain.keysExamined} docs={explain.docsExamined}
          </p>
        ))}
        <p className="font-mono text-caption text-on-surface-variant">{data.indexShowcase.indexCommand}</p>
      </section>

      <section
        data-testid="mongo-console-ttl"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">ttl exhibit · {data.ttlShowcase.collection}</p>
        <p data-testid="mongo-console-ttl-definition" className="font-mono text-caption text-on-surface">
          {Object.entries(data.ttlShowcase.indexDefinition)
            .map(([field, value]) => `${field}: ${value}`)
            .join(' · ')}
        </p>
        <p className="text-caption text-on-surface-variant">{data.ttlShowcase.evictionNote}</p>
      </section>

      <p data-testid="mongo-console-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function OperationRun({ operation }: { operation: ConsoleOperationRow }) {
  return (
    <section
      data-testid={`mongo-console-${operation.op}`}
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="font-mono text-caption text-on-surface">
        <span className="text-secondary">{operation.op}</span> — {operation.outcome}
      </p>
      <p className="font-mono text-caption text-on-surface-variant">{operation.command}</p>
      {operation.documents.map((document, index) => (
        <p key={index} className="font-mono text-caption text-on-surface-variant">
          {Object.entries(document)
            .map(([field, value]) => `${field}: ${value}`)
            .join(' · ')}
        </p>
      ))}
      <p className="text-caption text-on-surface-variant">{operation.description}</p>
    </section>
  );
}

export default DbMongoConsoleDemo;
