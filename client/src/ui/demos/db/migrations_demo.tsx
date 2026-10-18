import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { MigrationsDemo, MigrationRun } from '../../../domain/demo/db-migrations';

/**
 * DbMigrationsDemo — the databases-sql topic's transactional-DDL proof
 * (demo block id `db:migrations`). Two rehearsals over one scratch
 * table: the failing run applies two steps, PostgreSQL refuses the
 * third, and the ROLLBACK takes the CREATE TABLE and INSERT with it
 * (verified — the table does not exist); the succeeding run commits the
 * fixed sequence and is verified too. Every step's SQL and outcome,
 * the real error text, and both verifications on screen.
 */

type MigrationsStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: MigrationsDemo }
  | { state: 'failed'; failure: Failure };

export function DbMigrationsDemo() {
  const useCase = container.getDbMigrationsDemoUseCase;
  const [status, setStatus] = useState<MigrationsStatus>({ state: 'loading' });

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
      <p data-testid="mig-loading" className="text-body-sm text-on-surface-variant">
        rehearsing the migration…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the migration rehearsal" failure={status.failure} onRetry={runAgain} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <RunCard run={data.failing} failed />
      <RunCard run={data.succeeding} failed={false} />
      <p data-testid="mig-cleanup" className="text-caption text-on-surface-variant">
        {data.cleanupNote}
      </p>
      <p data-testid="mig-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function RunCard({ run, failed }: { run: MigrationRun; failed: boolean }) {
  return (
    <section
      data-testid="mig-run"
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="font-mono text-caption text-on-surface">
        <span className={failed ? 'text-error' : 'text-primary'}>
          {run.scenario} run
        </span>{' '}
        · committed: {String(run.committed)} · table exists after:{' '}
        {String(run.tableExistsAfter)}
        {run.rowCountAfter !== undefined ? ` · rows: ${run.rowCountAfter}` : ''}
      </p>
      {run.steps.map((step) => (
        <p key={step.description} data-testid="mig-step" className="font-mono text-caption text-on-surface-variant">
          <span className={step.outcome === 'applied' ? 'text-primary' : step.outcome.startsWith('failed') ? 'text-error' : 'text-on-surface-variant'}>
            [{step.outcome.split(':')[0]}]
          </span>{' '}
          {step.description} — <span className="text-secondary">{step.sql}</span>
        </p>
      ))}
      {run.failure !== undefined && (
        <p data-testid="mig-failure" className="font-mono text-caption text-error">
          {run.failure}
        </p>
      )}
    </section>
  );
}

export default DbMigrationsDemo;
