import { useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  GraphqlError,
  GraphqlPlayground,
  GraphqlRunResult,
} from '../../../domain/demo/graphql-playground';

/**
 * GraphqlPlaygroundDemo — the graphql topic's console (demo block id
 * `api:graphql-playground`). Loads the server's package — the endpoint,
 * the running schema's real SDL, and five curated operations — then acts
 * as a miniature GraphQL client: pick an example (or edit it), fire, and
 * read the raw response. Rounds POST directly to the LIVE /api/graphql,
 * so the mutation genuinely stores a post and the error example earns
 * its 200-with-errors — both rendered exactly as the protocol answered.
 *
 * Dependency flow mirrors the other demos: the use case resolves from
 * the container at render time (specs substitute fakes through the
 * container token), transport failures arrive as typed Failures inside
 * Results (the shared ErrorPanel offers recovery), and GraphQL-level
 * `errors` arrays are SUCCESSFUL results rendered inline — a failed
 * field is the protocol's honest answer, not the panel's.
 */

type PackageStatus =
  | { state: 'loading' }
  | { state: 'ready'; pkg: GraphqlPlayground }
  | { state: 'failed'; failure: Failure };

type RoundStatus =
  | { state: 'idle' }
  | { state: 'busy' }
  | { state: 'done'; result: GraphqlRunResult }
  | { state: 'failed'; failure: Failure };

const inputClass =
  'rounded-md border border-outline bg-surface-tint px-sm py-xxs font-mono ' +
  'text-caption text-on-surface focus:border-primary focus:outline-none';

const chipClass = (active: boolean): string =>
  active
    ? 'rounded-pill border border-primary bg-surface-tint px-sm py-xxs font-mono text-caption text-primary'
    : 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption ' +
      'text-on-surface-variant transition-colors hover:border-primary hover:text-primary';

const actionClass =
  'self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption ' +
  'uppercase tracking-wide text-on-surface transition-colors hover:border-primary ' +
  'hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

export function GraphqlPlaygroundDemo() {
  const useCase = container.getGraphqlPlaygroundDemoUseCase;
  const [pkg, setPkg] = useState<PackageStatus>({ state: 'loading' });
  const [editor, setEditor] = useState('');
  const [round, setRound] = useState<RoundStatus>({ state: 'idle' });
  const loadedOnce = useRef(false);

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    // Mount-once: the package (SDL + tour) loads the moment the demo
    // renders; the use case is container-resolved so specs swap the token.
    void useCase.playground().then((result) => {
      setPkg(
        result.ok
          ? { state: 'ready', pkg: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, []);

  const retryPackage = () => {
    setPkg({ state: 'loading' });
    void useCase.playground().then((result) => {
      setPkg(
        result.ok
          ? { state: 'ready', pkg: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  const trimmed = editor.trim();
  const emptyEditor = trimmed === '';

  const loadExample = (query: string) => {
    setEditor(query);
    setRound({ state: 'idle' });
  };

  const fire = () => {
    setRound({ state: 'busy' });
    void useCase.run(trimmed).then((result) => {
      setRound(
        result.ok
          ? { state: 'done', result: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (pkg.state === 'loading') {
    return (
      <p data-testid="gp-loading" className="text-body-sm text-on-surface-variant">
        reading the live schema and its curated tour…
      </p>
    );
  }

  if (pkg.state === 'failed') {
    return <ErrorPanel subject="the GraphQL playground" failure={pkg.failure} onRetry={retryPackage} />;
  }

  const { pkg: loaded } = pkg;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="gp-package" className="flex flex-col gap-sm">
        <p data-testid="gp-endpoint" className="font-mono text-caption text-on-surface">
          <span className="text-secondary">POST</span> {loaded.endpoint}
          <span className="text-on-surface-variant"> — the console below fires this editor at it.</span>
        </p>

        <div className="flex flex-wrap items-center gap-xxs">
          <span className="text-caption text-on-surface-variant">the tour:</span>
          {loaded.examples.map((example) => (
            <button
              key={example.id}
              type="button"
              data-testid="gp-example"
              title={example.description}
              onClick={() => loadExample(example.query)}
              className={chipClass(example.query === editor)}
            >
              {example.label}
            </button>
          ))}
        </div>

        <label className="flex flex-col gap-xxs">
          <span className="text-caption text-on-surface-variant">
            editor — the operation text, JSON-encoded as {"{ query }"} when it fires
          </span>
          <textarea
            data-testid="gp-editor"
            className={`${inputClass} min-h-[9rem]`}
            value={editor}
            onChange={(event) => {
              setEditor(event.target.value);
              if (round.state !== 'busy') setRound({ state: 'idle' });
            }}
            spellCheck={false}
          />
        </label>

        {emptyEditor && (
          <p data-testid="gp-empty-note" className="text-caption text-on-surface-variant">
            The editor is empty — load a tour example or write an operation before firing.
          </p>
        )}

        <div className="flex items-center gap-sm">
          <button
            type="button"
            data-testid="gp-run"
            onClick={fire}
            disabled={emptyEditor || round.state === 'busy'}
            className={actionClass}
          >
            Fire the query
          </button>
          {round.state === 'busy' && (
            <span data-testid="gp-busy" className="text-caption text-on-surface-variant">
              POSTing to the live endpoint…
            </span>
          )}
        </div>
      </section>

      {round.state === 'failed' && (
        <ErrorPanel
          subject="the GraphQL round"
          failure={round.failure}
          onRetry={fire}
        />
      )}

      {round.state === 'done' && <RoundResult result={round.result} />}

      <details data-testid="gp-sdl" className="rounded-md border border-outline px-sm py-xs">
        <summary className="cursor-pointer font-mono text-caption text-on-surface-variant">
          the schema (SDL, served live by the demo endpoint)
        </summary>
        <pre className="mt-xs overflow-x-auto font-mono text-caption text-on-surface-variant">
          {loaded.sdl}
        </pre>
      </details>

      <p data-testid="gp-reasoning" className="text-body-sm text-on-surface-variant">
        {loaded.reasoning}
      </p>
    </div>
  );
}

function RoundResult({ result }: { result: GraphqlRunResult }) {
  return (
    <section data-testid="gp-result" className="flex flex-col gap-sm">
      {result.errors !== undefined && result.errors.length > 0 && (
        <div
          data-testid="gp-result-errors"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="text-caption text-on-surface-variant">
            errors (a 200 carried them — this is the protocol’s failure shape):
          </p>
          {result.errors.map((error, index) => (
            <ErrorItem key={index} error={error} />
          ))}
        </div>
      )}
      {result.data !== undefined && (
        <div data-testid="gp-result-data" className="rounded-md border border-outline px-sm py-xs">
          <pre className="overflow-x-auto font-mono text-caption text-on-surface-variant">
            {JSON.stringify(result.data, null, 2)}
          </pre>
        </div>
      )}
      {result.data === undefined && (result.errors === undefined || result.errors.length === 0) && (
        <p data-testid="gp-result-empty" className="font-mono text-caption text-on-surface-variant">
          {'{ }'}
        </p>
      )}
    </section>
  );
}

function ErrorItem({ error }: { error: GraphqlError }) {
  const code =
    error.extensions !== undefined && typeof error.extensions.code === 'string'
      ? error.extensions.code
      : undefined;
  const where =
    error.locations !== undefined && error.locations.length > 0
      ? ` at ${String(error.locations[0]?.line)}:${String(error.locations[0]?.column)}`
      : '';
  const path = error.path !== undefined ? ` · path: ${error.path.join('.')}` : '';
  return (
    <p className="font-mono text-caption text-on-surface">
      <span className="text-error">{error.message}</span>
      <span className="text-on-surface-variant">
        {where}
        {path}
        {code !== undefined ? ` · code: ${code}` : ''}
      </span>
    </p>
  );
}

export default GraphqlPlaygroundDemo;
