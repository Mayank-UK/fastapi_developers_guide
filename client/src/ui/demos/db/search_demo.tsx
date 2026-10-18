import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { SearchDemo } from '../../../domain/demo/db-search';

/**
 * DbSearchDemo — the databases-sql topic's full-text search lab (demo
 * block id `db:search`). The parsed (stemmed) tsquery, ranked matches
 * with ts_rank scores and highlighted headlines, and BOTH EXPLAIN plans
 * captured live: the GIN bitmap index scan vs the no-index seq scan
 * that recomputes the vector per row. Search anything — free input
 * dissolves safely into lexemes.
 */

type SearchStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: SearchDemo; searching: boolean }
  | { state: 'failed'; failure: Failure };

export function DbSearchDemo() {
  const useCase = container.getDbSearchDemoUseCase;
  const [status, setStatus] = useState<SearchStatus>({ state: 'loading' });
  const [queryDraft, setQueryDraft] = useState('');

  useEffect(() => {
    let cancelled = false;
    void useCase.run().then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, searching: false }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase]);

  const search = (q: string | undefined) => {
    setStatus((current) =>
      current.state === 'ready' ? { ...current, searching: true } : current,
    );
    void useCase.run(q).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, searching: false }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="search-loading" className="text-body-sm text-on-surface-variant">
        ranking full-text matches…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the search lab" failure={status.failure} onRetry={() => search(undefined)} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="search-input" className="flex gap-xxs">
        <input
          data-testid="search-field"
          type="text"
          value={queryDraft}
          maxLength={200}
          onChange={(event) => setQueryDraft(event.target.value)}
          placeholder={data.query}
          className="w-full rounded-md border border-outline bg-surface px-sm py-xxs font-mono text-caption text-on-surface"
        />
        <button
          type="button"
          data-testid="search-run"
          onClick={() => search(queryDraft === '' ? undefined : queryDraft)}
          className="rounded-pill border border-outline px-sm py-xxs text-caption text-on-surface transition-colors hover:border-primary hover:text-primary"
        >
          {status.searching ? 'searching…' : 'search'}
        </button>
      </section>

      <section
        data-testid="search-matches"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          plainto_tsquery → <span className="text-secondary">{data.parsedQuery}</span> ·{' '}
          {data.matchCount} match(es)
        </p>
        {data.matches.map((match) => (
          <article key={match.id} data-testid="search-match" className="flex flex-col gap-xxs">
            <p className="font-mono text-caption text-on-surface">
              <span className="text-secondary">{match.rank.toFixed(4)}</span> {match.title}
            </p>
            <p
              className="text-caption text-on-surface-variant"
              dangerouslySetInnerHTML={{ __html: match.headline }}
            />
          </article>
        ))}
        {data.matches.length === 0 && (
          <p className="text-caption text-on-surface-variant">
            no post matches — zero hits is data, not an error.
          </p>
        )}
      </section>

      <section data-testid="search-plans" className="flex flex-col gap-xs">
        <PlanCard label="indexed (GIN)" lines={data.indexedPlan} accent />
        <PlanCard label="naive (recompute per row)" lines={data.naivePlan} accent={false} />
        <p className="text-caption text-on-surface-variant">{data.planNote}</p>
      </section>

      <p data-testid="search-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function PlanCard({ label, lines, accent }: { label: string; lines: string[]; accent: boolean }) {
  return (
    <div className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
      <p className={`font-mono text-caption ${accent ? 'text-primary' : 'text-on-surface'}`}>
        {label}
      </p>
      {lines.slice(0, 5).map((line, index) => (
        <p key={index} className="font-mono text-caption whitespace-pre text-on-surface-variant">
          {line}
        </p>
      ))}
    </div>
  );
}

export default DbSearchDemo;
