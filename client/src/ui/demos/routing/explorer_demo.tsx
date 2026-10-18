import { useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  BoundParam,
  ExplorerMethod,
  RoutingExplorerData,
  RoutingExplorerRequest,
} from '../../../domain/demo/routing-explorer';

/**
 * RoutingExplorerDemo — the routing topic's route matcher (demo block id
 * `routing:explorer`). A miniature URL bar: pick a method, type a path
 * (a query string is welcome — it becomes queryParams), and match it
 * against the live app's declared route table. The verdict renders with
 * everything the router would have done: the matched template and the
 * parameters it binds, the 307 redirect target, the 405's allowed
 * methods, or the 404's nearest declared paths — each with the server's
 * one-sentence reasoning.
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token — the documented replace-a-singleton seam), failures arrive as
 * typed Failures inside Results, and the shared ErrorPanel offers
 * recovery. The path is validated client-side first (must start with /)
 * because the endpoint's pattern guard would otherwise answer a 422 —
 * honest, but the form can catch it earlier.
 */

const METHODS: readonly ExplorerMethod[] = [
  'GET',
  'POST',
  'PUT',
  'PATCH',
  'DELETE',
  'HEAD',
  'OPTIONS',
];

type MatchStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: RoutingExplorerData }
  | { state: 'error'; failure: Failure };

const inputClass =
  'w-full rounded-md border border-outline bg-surface-tint px-sm py-xxs ' +
  'font-mono text-caption text-on-surface placeholder:text-on-surface-variant ' +
  'focus:border-primary focus:outline-none';

export function RoutingExplorerDemo() {
  const useCase = container.getRoutingExplorerDemoUseCase;
  const [method, setMethod] = useState<ExplorerMethod>('GET');
  const [path, setPath] = useState('/api/content/routing');
  const [status, setStatus] = useState<MatchStatus>({ state: 'idle' });
  const [lastRequest, setLastRequest] = useState<RoutingExplorerRequest | null>(null);

  const trimmedPath = path.trim();
  const pathIsInvalid = trimmedPath !== '' && !trimmedPath.startsWith('/');
  const matchDisabled = status.state === 'loading' || pathIsInvalid || trimmedPath === '';

  const fire = (request: RoutingExplorerRequest) => {
    setLastRequest(request);
    setStatus({ state: 'loading' });
    void useCase.execute(request).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  };

  const match = () => {
    fire({ method, path: trimmedPath });
  };

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="rx-form" className="flex flex-col gap-sm">
        <div className="flex flex-wrap items-center gap-xs">
          <span className="text-caption text-on-surface-variant">method</span>
          {METHODS.map((candidate) => (
            <button
              key={candidate}
              type="button"
              data-testid={`rx-method-${candidate.toLowerCase()}`}
              aria-pressed={method === candidate}
              onClick={() => setMethod(candidate)}
              className={
                method === candidate
                  ? 'rounded-pill border border-primary bg-surface-tint px-sm py-xxs font-mono text-caption uppercase tracking-wide text-primary'
                  : 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption uppercase tracking-wide text-on-surface-variant transition-colors hover:border-primary hover:text-primary'
              }
            >
              {candidate}
            </button>
          ))}
        </div>

        <label className="flex flex-col gap-xxs">
          <span className="text-caption text-on-surface-variant">
            path (a query string is parsed as queryParams)
          </span>
          <input
            data-testid="rx-path"
            className={inputClass}
            value={path}
            onChange={(event) => setPath(event.target.value)}
            placeholder="/api/content/routing"
          />
        </label>
        {pathIsInvalid && (
          <p data-testid="rx-path-warning" className="text-caption text-error">
            Paths are absolute — start with a slash.
          </p>
        )}

        <div className="flex items-center gap-sm">
          <button
            type="button"
            data-testid="rx-match"
            onClick={match}
            disabled={matchDisabled}
            className="self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            Match
          </button>
          {status.state === 'loading' && (
            <span data-testid="rx-loading" className="text-caption text-on-surface-variant">
              walking the table…
            </span>
          )}
        </div>
      </section>

      {status.state === 'error' && (
        <ErrorPanel
          subject="the route explorer"
          failure={status.failure}
          onRetry={lastRequest === null ? undefined : () => fire(lastRequest)}
        />
      )}

      {status.state === 'ready' && <MatchResult data={status.data} />}

      {status.state === 'idle' && (
        <p data-testid="rx-idle" className="text-body-sm text-on-surface-variant">
          Pick a method and a path, then match — the server replays the
          router's walk and reports the outcome. Try HEAD against
          /api/health.
        </p>
      )}
    </div>
  );
}

function MatchResult({ data }: { data: RoutingExplorerData }) {
  const params = [...data.pathParams, ...data.queryParams];
  return (
    <section data-testid="rx-result" className="flex flex-col gap-sm">
      <p data-testid="rx-request-line" className="font-mono text-body-sm text-on-surface">
        <span className="text-secondary">{data.request.method}</span>{' '}
        {data.request.path}
      </p>

      <p data-testid="rx-outcome" className="font-mono text-caption">
        <span
          className={
            data.outcome === 'matched'
              ? 'rounded-pill border border-primary px-sm py-xxs uppercase tracking-wide text-primary'
              : 'rounded-pill border border-outline px-sm py-xxs uppercase tracking-wide text-on-surface-variant'
          }
        >
          {data.outcome.replaceAll('_', ' ')}
        </span>
        <span className="ml-xs text-on-surface-variant">
          · one of {data.routeCount} declared templates
        </span>
      </p>

      {data.matchedPath !== undefined && (
        <p data-testid="rx-matched" className="font-mono text-body-sm text-on-surface">
          template <span className="text-primary">{data.matchedPath}</span>
          {data.matchedMethods !== undefined && (
            <span className="text-on-surface-variant"> · {data.matchedMethods.join(' ')}</span>
          )}
          {data.matchedTags !== undefined && data.matchedTags.length > 0 && (
            <span className="text-on-surface-variant"> · tags: {data.matchedTags.join(', ')}</span>
          )}
        </p>
      )}

      {data.redirectTarget !== undefined && (
        <p data-testid="rx-redirect" className="font-mono text-body-sm text-on-surface">
          307 → <span className="text-primary">{data.redirectTarget}</span>
        </p>
      )}

      {data.allowedMethods !== undefined && (
        <p data-testid="rx-allowed" className="font-mono text-body-sm text-on-surface">
          declared methods: <span className="text-primary">{data.allowedMethods.join(' ')}</span>
        </p>
      )}

      {params.length > 0 && (
        <div data-testid="rx-params" className="flex flex-col gap-xxs">
          <p className="text-caption text-on-surface-variant">bound parameters:</p>
          {params.map((param) => (
            <ParamRow key={`${param.source}-${param.name}`} param={param} />
          ))}
        </div>
      )}

      {data.nearMisses !== undefined && data.nearMisses.length > 0 && (
        <div data-testid="rx-near" className="flex flex-col gap-xxs">
          <p className="text-caption text-on-surface-variant">
            nearest declared paths (you probably meant one of these):
          </p>
          <div className="flex flex-wrap gap-xxs">
            {data.nearMisses.map((miss) => (
              <span
                key={miss.path}
                className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant"
              >
                {miss.path} · {miss.methods.join(' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      <p data-testid="rx-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </section>
  );
}

function ParamRow({ param }: { param: BoundParam }) {
  return (
    <p className="font-mono text-caption text-on-surface">
      <span
        className={
          param.source === 'path'
            ? 'rounded-pill border border-primary px-sm py-xxs text-primary'
            : 'rounded-pill border border-outline px-sm py-xxs text-on-surface-variant'
        }
      >
        {param.source}
      </span>{' '}
      {param.name} = {param.value}
    </p>
  );
}

export default RoutingExplorerDemo;
