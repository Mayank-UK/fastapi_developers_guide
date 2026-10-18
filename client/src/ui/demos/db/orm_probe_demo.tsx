import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { OrmProbeDemo, StrategyCard } from '../../../domain/demo/db-orm-probe';

/**
 * DbOrmProbeDemo — the sqlalchemy-orm topic's probe (demo block id
 * `db:orm-probe`). The same access pattern — load posts, touch each
 * post's author and comments — under three loading strategies, with
 * REAL query counts: lazy shows the N+1 shape, selectinload batches it
 * away, joinedload collapses it to one statement. Below the strategies,
 * the session's two proofs: identity map (two gets → ONE SELECT, same
 * object) and dirty checking (one field mutated → exactly one UPDATE,
 * rolled back so every run repeats identically).
 */

type ProbeStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: OrmProbeDemo }
  | { state: 'failed'; failure: Failure };

const STRATEGY_NOTES: Record<string, string> = {
  lazy: '1 + A + N — per-relationship SELECTs on touch (the N+1 shape)',
  joinedload: 'one statement — everything OUTER JOINed in',
  selectinload: 'one SELECT per table, follow-ups batched with IN',
};

export function DbOrmProbeDemo() {
  const useCase = container.getDbOrmProbeDemoUseCase;
  const [status, setStatus] = useState<ProbeStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.run().then((result) => {
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
  }, [useCase]);

  const runAgain = () => {
    setStatus({ state: 'loading' });
    void useCase.run().then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="orm-probe-loading" className="text-body-sm text-on-surface-variant">
        running the strategies…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the ORM probe" failure={status.failure} onRetry={runAgain} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <p data-testid="orm-probe-subject" className="text-caption text-on-surface-variant">
        {data.postCount} published posts, each post's author and comments touched —
        starting from <span className="text-secondary">{data.firstPostTitle}</span>.
        Identical results across strategies:{' '}
        <span className={data.resultsMatch ? 'text-primary' : 'text-error'}>
          {String(data.resultsMatch)}
        </span>
        .
      </p>
      {data.strategies.map((card) => (
        <StrategyRun key={card.strategy} card={card} />
      ))}
      <section
        data-testid="orm-probe-identity"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">identity map</p>
        <p data-testid="orm-probe-identity-proof" className="font-mono text-caption text-on-surface">
          two session.get() calls → {data.identityMap.selectCount} SELECT · same
          object: {String(data.identityMap.sameObject)}
        </p>
        <p className="text-caption text-on-surface-variant">
          The second get is answered from the session's identity map — the map is
          keyed by primary key, one row one object, no SQL.
        </p>
      </section>
      <section
        data-testid="orm-probe-dirty"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">dirty checking</p>
        <p data-testid="orm-probe-dirty-proof" className="font-mono text-caption text-on-surface">
          {data.dirtyCheck.field}: {data.dirtyCheck.before} → {data.dirtyCheck.after} ·{' '}
          {data.dirtyCheck.updateCount} UPDATE on flush · committed:{' '}
          {String(data.dirtyCheck.committed)}
        </p>
        <p data-testid="orm-probe-dirty-sql" className="font-mono text-caption text-on-surface-variant">
          {data.dirtyCheck.updateSql}
        </p>
        <p className="text-caption text-on-surface-variant">
          The session diffs objects against their loaded state and emits the minimal
          change set — note the version guard in the WHERE, then rolled back.
        </p>
      </section>
      <p data-testid="orm-probe-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function StrategyRun({ card }: { card: StrategyCard }) {
  return (
    <section
      data-testid="orm-probe-strategy"
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="font-mono text-caption text-on-surface">
        <span className="text-secondary">{card.strategy}</span> — {card.sqlCount}{' '}
        statement(s) · {card.elapsedMs.toFixed(1)} ms
      </p>
      <p className="text-caption text-on-surface-variant">
        {STRATEGY_NOTES[card.strategy] ?? ''} · {card.authorCount} authors ·{' '}
        {card.commentTotal} comments touched
      </p>
      {card.statements.slice(0, 3).map((statement, index) => (
        <p
          key={index}
          data-testid="orm-probe-statement"
          className="font-mono text-caption text-on-surface-variant"
        >
          {statement.length > 110 ? `${statement.slice(0, 110)}…` : statement}
        </p>
      ))}
      {card.statements.length > 3 && (
        <p className="font-mono text-caption text-on-surface-variant">
          … +{card.statements.length - 3} more (full list in the API payload)
        </p>
      )}
    </section>
  );
}

export default DbOrmProbeDemo;
