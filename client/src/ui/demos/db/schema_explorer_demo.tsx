import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { SchemaExplorer, TableFocus } from '../../../domain/demo/schema-explorer';

/**
 * SchemaExplorerDemo — the sql-schema topic's live schema view (demo
 * block id `db:schema-explorer`). Loads the roster of the REAL dev
 * PostgreSQL (table summaries with column/FK/CHECK/index counts), and
 * drilling into a table re-fetches with ?table= to render its full
 * anatomy: columns with types/nullability/raw defaults, the primary
 * key, foreign keys with ON DELETE behaviors, CHECK definitions
 * verbatim, and every index with kind, uniqueness, and partial WHERE.
 * Everything on screen was introspected live — a new migration changes
 * this component's answer.
 *
 * Dependency flow mirrors the other demos: the use case resolves from
 * the container at render time (specs substitute fakes through the
 * container token), failures arrive as typed Failures inside Results,
 * and the shared ErrorPanel offers recovery.
 */

type ExplorerStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: SchemaExplorer; drilling: boolean }
  | { state: 'failed'; failure: Failure };

export function SchemaExplorerDemo() {
  const useCase = container.getSchemaExplorerDemoUseCase;
  const [status, setStatus] = useState<ExplorerStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.roster().then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, drilling: false }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase]);

  const retry = () => {
    setStatus({ state: 'loading' });
    void useCase.roster().then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, drilling: false }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  const drill = (table: string) => {
    setStatus((current) =>
      current.state === 'ready' ? { ...current, drilling: true } : current,
    );
    void useCase.drill(table).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, drilling: false }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="se-loading" className="text-body-sm text-on-surface-variant">
        introspecting the live schema…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the schema explorer" failure={status.failure} onRetry={retry} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="se-roster" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">
          live tables of database <span className="text-secondary">{data.databaseName}</span> —
          click one to drill into its anatomy:
        </p>
        <div className="flex flex-wrap gap-xxs">
          {data.tables.map((table) => (
            <button
              key={table.name}
              type="button"
              data-testid="se-table-btn"
              onClick={() => drill(table.name)}
              className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface transition-colors hover:border-primary hover:text-primary"
            >
              <span className="text-secondary">{table.name}</span> · {table.columnCount} cols ·{' '}
              {table.indexCount} idx
            </button>
          ))}
        </div>
      </section>

      {status.drilling && (
        <p data-testid="se-drilling" className="text-caption text-on-surface-variant">
          drilling…
        </p>
      )}

      {data.focus !== undefined && <FocusCard focus={data.focus} />}

      <p data-testid="se-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function FocusCard({ focus }: { focus: TableFocus }) {
  return (
    <section
      data-testid="se-focus"
      className="flex flex-col gap-xs rounded-md border border-outline px-sm py-xs"
    >
      <p className="font-mono text-caption text-on-surface">
        <span className="text-secondary">{focus.name}</span> — {focus.columns.length} columns · pk{' '}
        {focus.primaryKey.join(', ')}
      </p>

      <div className="overflow-x-auto rounded-md border border-outline">
        <table className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">column</th>
              <th scope="col" className="px-sm py-xxs">type</th>
              <th scope="col" className="px-sm py-xxs">nullable</th>
              <th scope="col" className="px-sm py-xxs">default</th>
            </tr>
          </thead>
          <tbody>
            {focus.columns.map((column) => (
              <tr key={column.name} data-testid="se-col-row" className="border-t border-outline">
                <td className="px-sm py-xxs text-secondary">{column.name}</td>
                <td className="px-sm py-xxs text-on-surface">{column.type}</td>
                <td className="px-sm py-xxs text-on-surface-variant">
                  {column.nullable ? 'yes' : 'no'}
                </td>
                <td className="px-sm py-xxs text-on-surface-variant">
                  {column.defaultValue ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {focus.foreignKeys.length > 0 && (
        <p data-testid="se-fks" className="font-mono text-caption text-on-surface-variant">
          {focus.foreignKeys.map((fk) => (
            <span key={fk.name} className="mr-sm">
              {fk.columns.join(', ')} →{' '}
              <span className="text-secondary">
                {fk.referencesTable}({fk.referencesColumns.join(', ')})
              </span>{' '}
              ON DELETE {fk.onDelete}
            </span>
          ))}
        </p>
      )}

      {focus.checks.length > 0 && (
        <div data-testid="se-checks" className="flex flex-col gap-xxs">
          {focus.checks.map((check) => (
            <p key={check.name} className="font-mono text-caption text-on-surface-variant">
              <span className="text-secondary">{check.name}</span> {check.definition}
            </p>
          ))}
        </div>
      )}

      <div data-testid="se-indexes" className="flex flex-col gap-xxs">
        {focus.indexes.map((index) => (
          <p key={index.name} className="font-mono text-caption text-on-surface-variant">
            <span className="text-secondary">{index.name}</span> {index.kind} ({index.columns.join(', ')})
            {index.unique ? ' · unique' : ''}
            {index.primary ? ' · primary' : ''}
            {index.where !== undefined ? ` · where ${index.where}` : ''}
          </p>
        ))}
      </div>
    </section>
  );
}

export default SchemaExplorerDemo;
