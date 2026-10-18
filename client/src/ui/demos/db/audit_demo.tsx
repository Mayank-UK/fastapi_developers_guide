import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { AuditDemo } from '../../../domain/demo/db-audit';

/**
 * DbAuditDemo — the databases-sql topic's audit proof (demo block id
 * `db:audit`). Both halves of the in-transaction audit pattern, live:
 * a committed status flip whose audit row is read back from audit_log,
 * and a rolled-back change (audit written first, then the title CHECK
 * trips in the SAME transaction) that leaves zero audit rows — counted,
 * not claimed. The post's history grows by one audited row per run.
 */

type AuditStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: AuditDemo }
  | { state: 'failed'; failure: Failure };

export function DbAuditDemo() {
  const useCase = container.getDbAuditDemoUseCase;
  const [status, setStatus] = useState<AuditStatus>({ state: 'loading' });

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
      <p data-testid="audit-loading" className="text-body-sm text-on-surface-variant">
        running both halves of the proof…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the audit proof" failure={status.failure} onRetry={runAgain} />;
  }

  const { data } = status;
  const { committed, rolledBack } = data;

  return (
    <div className="flex flex-col gap-md">
      <p data-testid="audit-subject" className="text-caption text-on-surface-variant">
        the subject is <span className="text-secondary">{data.postTitle}</span> — each run
        flips its status and audits itself.
      </p>

      <section
        data-testid="audit-committed"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          committed — change visible: {String(committed.changeVisible)}
        </p>
        <p className="font-mono text-caption text-on-surface">
          status {committed.statusBefore} →{' '}
          <span className="text-secondary">{committed.statusAfter}</span>, audit row #
          {committed.auditRow.id} ({committed.auditRow.actor}):{' '}
          {committed.auditRow.changes}
        </p>
      </section>

      <section
        data-testid="audit-rolled-back"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-error">
          rolled back — audit rows added: {rolledBack.auditRowsAdded}, change visible:{' '}
          {String(rolledBack.changeVisible)}
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          attempted title: {rolledBack.attemptedTitle}
        </p>
        <p className="font-mono text-caption text-error">{rolledBack.failure}</p>
      </section>

      <section
        data-testid="audit-history"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          audit history — {data.historyCount} row(s), one more per run
        </p>
        {data.history.map((event) => (
          <p key={event.id} data-testid="audit-history-row" className="font-mono text-caption text-on-surface-variant">
            #{event.id} {event.occurredAt} · {event.actor} · {event.action} ·{' '}
            {event.changes}
          </p>
        ))}
      </section>

      <p data-testid="audit-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default DbAuditDemo;
