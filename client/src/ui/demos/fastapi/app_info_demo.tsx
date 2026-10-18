import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { GetFastApiAppInfoDemoUseCase } from '../../../domain/demo/get-fastapi-app-info-demo-usecase';
import type {
  FastApiAppInfoData,
  RouteEntry,
} from '../../../domain/demo/fastapi-app-info';

/**
 * FastApiAppInfoDemo — the fastapi-fundamentals topic's live demo (demo
 * block id `fastapi:app-info`). It renders the payload of
 * GET /api/demo/fastapi/app-info, which the server computes by
 * introspecting the very app serving it: identity and environment, the
 * docs mounts (linked, new tab), the fastapi/starlette/pydantic stack, the
 * registered middleware and exception handlers, and the full route table
 * built from the public OpenAPI schema — grouped by router prefix.
 *
 * Dependency flow mirrors the other demos: the hook resolves the use case
 * from the container (its default parameter is the spec seam — tests
 * substitute fakes through the container token), failures arrive as typed
 * Failures inside Results, and `retry` re-runs the load.
 */

type AppInfoStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: FastApiAppInfoData }
  | { state: 'error'; failure: Failure };

export function useFastApiAppInfoDemo(
  useCase: GetFastApiAppInfoDemoUseCase = container.getFastApiAppInfoDemoUseCase,
): { status: AppInfoStatus; retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<AppInfoStatus>({ state: 'idle' });

  useEffect(() => {
    let cancelled = false;
    setStatus({ state: 'loading' });

    void useCase.execute().then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setStatus({ state: 'ready', data: result.value });
      } else {
        setStatus({ state: 'error', failure: result.failure });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [useCase, attempt]);

  const retry = () => setAttempt((current) => current + 1);
  return { status, retry };
}

export function FastApiAppInfoDemo() {
  const { status, retry } = useFastApiAppInfoDemo();

  if (status.state === 'idle' || status.state === 'loading') {
    return (
      <p data-testid="fastapi-app-info-loading" className="text-body-sm text-on-surface-variant">
        introspecting the running app…
      </p>
    );
  }

  if (status.state === 'error') {
    return (
      <ErrorPanel subject="the app-info demo" failure={status.failure} onRetry={retry} />
    );
  }

  const { docs, stack } = status.data;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="fai-facts" className="flex flex-wrap items-center gap-xs">
        <span className="font-display text-title-sm text-on-surface">{status.data.title}</span>
        <span className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant">
          v{status.data.version}
        </span>
        <span className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-secondary">
          env: {status.data.environment}
        </span>
      </section>

      <section data-testid="fai-docs" className="flex flex-wrap items-center gap-xs">
        <span className="text-caption text-on-surface-variant">docs mounts:</span>
        {docs.docsUrl !== undefined && <DocsLink testId="fai-docs-swagger" label="Swagger UI" url={docs.docsUrl} />}
        {docs.redocUrl !== undefined && <DocsLink testId="fai-docs-redoc" label="ReDoc" url={docs.redocUrl} />}
        {docs.openapiUrl !== undefined && (
          <DocsLink testId="fai-docs-openapi" label="openapi.json" url={docs.openapiUrl} />
        )}
      </section>

      <section data-testid="fai-stack" className="flex flex-wrap items-center gap-xs">
        <span className="text-caption text-on-surface-variant">the stack:</span>
        <Chip label={`fastapi ${stack.fastapi}`} />
        <Chip label={`starlette ${stack.starlette}`} />
        <Chip label={`pydantic ${stack.pydantic}`} />
      </section>

      <section data-testid="fai-wiring" className="flex flex-col gap-xs">
        <div className="flex flex-wrap items-center gap-xs">
          <span className="text-caption text-on-surface-variant">middleware:</span>
          {status.data.middleware.map((name) => (
            <Chip key={name} label={name} />
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-xs">
          <span className="text-caption text-on-surface-variant">exception handlers:</span>
          {status.data.exceptionHandlers.map((registration) => (
            <span
              key={registration.exception}
              data-testid="fai-handler"
              className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant"
            >
              {registration.exception} → {registration.handler}
            </span>
          ))}
        </div>
      </section>

      <RouteTable routes={status.data.routes} />
    </div>
  );
}

/** Group key = the path minus its last segment — the router prefix. */
function routerPrefix(path: string): string {
  const cut = path.lastIndexOf('/');
  return cut > 0 ? path.slice(0, cut) : path;
}

function RouteTable({ routes }: { routes: readonly RouteEntry[] }) {
  const groups = new Map<string, RouteEntry[]>();
  for (const route of routes) {
    const prefix = routerPrefix(route.path);
    const bucket = groups.get(prefix);
    if (bucket === undefined) {
      groups.set(prefix, [route]);
    } else {
      bucket.push(route);
    }
  }

  return (
    <section data-testid="fai-routes" className="flex flex-col gap-sm">
      <p className="text-caption text-on-surface-variant">
        the declared API ({routes.length} paths, from the OpenAPI schema — grouped by
        router prefix; the docs mounts serve this contract but are not part of it):
      </p>
      {[...groups.entries()].map(([prefix, entries]) => (
        <div key={prefix} data-testid="fai-route-group" className="flex flex-col gap-xxs">
          <p className="font-mono text-caption text-secondary">{prefix}</p>
          <div className="overflow-x-auto rounded-md border border-outline">
            <table className="w-full text-left font-mono text-caption">
              <thead className="bg-surface-tint text-on-surface-variant">
                <tr>
                  <th scope="col" className="px-sm py-xxs">path</th>
                  <th scope="col" className="px-sm py-xxs">methods</th>
                  <th scope="col" className="px-sm py-xxs">tags</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((route) => (
                  <tr key={route.path} className="border-t border-outline">
                    <td className="px-sm py-xxs text-on-surface">{route.path}</td>
                    <td className="px-sm py-xxs text-secondary">{route.methods.join(' · ')}</td>
                    <td className="px-sm py-xxs text-on-surface-variant">
                      {route.tags.length > 0 ? route.tags.join(', ') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </section>
  );
}

function DocsLink({ testId, label, url }: { testId: string; label: string; url: string }) {
  return (
    <a
      data-testid={testId}
      href={url}
      target="_blank"
      rel="noreferrer"
      className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-primary transition-colors hover:border-primary"
    >
      {label} ↗
    </a>
  );
}

function Chip({ label }: { label: string }) {
  return (
    <span className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant">
      {label}
    </span>
  );
}

export default FastApiAppInfoDemo;
