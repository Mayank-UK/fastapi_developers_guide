import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { DocsHub, DocsOperation, DocsShowcase } from '../../../domain/demo/docs-link';

/**
 * DocsLinkDemo — the api-documentation topic's hub (demo block id
 * `api:docs-link`). Renders the payload of GET /api/demo/api/docs-link,
 * which the server computes from the RUNNING app's own OpenAPI schema:
 * links to the rendered docs (Swagger UI, ReDoc) and the contract
 * itself, the info identity with the spec version, the path/operation/
 * schema counts, every tag area with its methods, the posts resource's
 * four generated operations with their operationIds and documented
 * responses, and the showcase slice — the POST /api/posts operation
 * exactly as generated, $ref names included, so the reader watches a
 * declaration become a documented operation.
 *
 * Dependency flow mirrors the other demos: the use case resolves from
 * the container at render time (specs substitute fakes through the
 * container token), failures arrive as typed Failures inside Results,
 * and the shared ErrorPanel offers recovery.
 */

type HubStatus =
  | { state: 'loading' }
  | { state: 'ready'; hub: DocsHub }
  | { state: 'failed'; failure: Failure };

export function DocsLinkDemo() {
  const useCase = container.getDocsLinkDemoUseCase;
  const [status, setStatus] = useState<HubStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.hub().then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', hub: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
    // Mount-once: the hub is observational — retry re-runs the effect.
  }, [useCase]);

  const retry = () => {
    setStatus({ state: 'loading' });
    void useCase.hub().then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', hub: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="dl-loading" className="text-body-sm text-on-surface-variant">
        reading the running app's generated documentation…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the documentation hub" failure={status.failure} onRetry={retry} />;
  }

  const { hub } = status;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="dl-links" className="flex flex-wrap items-center gap-xs">
        <span className="text-caption text-on-surface-variant">the contract, rendered:</span>
        {hub.docs.swaggerUi !== undefined && (
          <HubLink testId="dl-link-swagger" label="Swagger UI" url={hub.docs.swaggerUi} />
        )}
        {hub.docs.redoc !== undefined && (
          <HubLink testId="dl-link-redoc" label="ReDoc" url={hub.docs.redoc} />
        )}
        {hub.docs.openapiJson !== undefined && (
          <HubLink testId="dl-link-openapi" label="openapi.json" url={hub.docs.openapiJson} />
        )}
      </section>

      <section data-testid="dl-facts" className="flex flex-wrap items-center gap-xs">
        <span className="font-display text-title-sm text-on-surface">{hub.infoTitle}</span>
        <Chip label={`v${hub.infoVersion}`} />
        <Chip label={`OpenAPI ${hub.openapiVersion}`} />
        <Chip label={`${hub.pathCount} paths`} />
        <Chip label={`${hub.operationCount} operations`} />
        <Chip label={`${hub.schemaCount} schemas`} />
      </section>

      <section data-testid="dl-areas" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">
          tag areas ({hub.areaCount}) — the grouping the renderers organize by:
        </p>
        <div className="flex flex-wrap gap-xxs">
          {hub.areas.map((area) => (
            <span
              key={area.tag}
              data-testid="dl-area"
              className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant"
            >
              <span className="text-secondary">{area.tag}</span> · {area.methods.join(' ')} ·{' '}
              {area.operations} op{area.operations === 1 ? '' : 's'}
            </span>
          ))}
        </div>
      </section>

      <PostsOperations operations={hub.postsOperations} schemaNames={hub.schemaNames} />
      {hub.showcase !== undefined && <Showcase showcase={hub.showcase} />}

      <p data-testid="dl-reasoning" className="text-body-sm text-on-surface-variant">
        {hub.reasoning}
      </p>
    </div>
  );
}

function PostsOperations({
  operations,
  schemaNames,
}: {
  operations: readonly DocsOperation[];
  schemaNames: readonly string[];
}) {
  return (
    <section data-testid="dl-posts" className="flex flex-col gap-xxs">
      <p className="text-caption text-on-surface-variant">
        the posts resource as /openapi.json documents it ({operations.length} operations; the
        component names below are real entries of components/schemas):
      </p>
      <div className="overflow-x-auto rounded-md border border-outline">
        <table className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">method</th>
              <th scope="col" className="px-sm py-xxs">path</th>
              <th scope="col" className="px-sm py-xxs">operationId</th>
              <th scope="col" className="px-sm py-xxs">responses</th>
            </tr>
          </thead>
          <tbody>
            {operations.map((operation) => (
              <tr
                key={`${operation.method} ${operation.path}`}
                data-testid="dl-posts-row"
                className="border-t border-outline"
              >
                <td className="px-sm py-xxs text-secondary">{operation.method}</td>
                <td className="px-sm py-xxs text-on-surface">{operation.path}</td>
                <td className="px-sm py-xxs text-on-surface-variant">{operation.operationId}</td>
                <td className="px-sm py-xxs text-on-surface-variant">
                  {operation.responses.join(' · ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p data-testid="dl-schemas" className="font-mono text-caption text-on-surface-variant">
        {schemaNames.slice(0, 8).join(' · ')}
        {schemaNames.length > 8 ? ` · … (${schemaNames.length} total)` : ''}
      </p>
    </section>
  );
}

function Showcase({ showcase }: { showcase: DocsShowcase }) {
  return (
    <section
      data-testid="dl-showcase"
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="font-mono text-caption text-on-surface">
        <span className="text-secondary">{showcase.method}</span> {showcase.path} —{' '}
        {showcase.summary}
      </p>
      <p className="text-body-sm text-on-surface">{showcase.description}</p>
      <p className="font-mono text-caption text-on-surface-variant">
        operationId: <span className="text-secondary">{showcase.operationId}</span> · tags:{' '}
        {showcase.tags.join(', ')}
      </p>
      <p className="font-mono text-caption text-on-surface-variant">
        {showcase.requestSchema !== undefined && <>request → {showcase.requestSchema} · </>}
        {showcase.successStatus !== undefined && (
          <>
            {showcase.successStatus} → {showcase.successSchema} ·{' '}
          </>
        )}
        {showcase.validationSchema !== undefined && <>422 → {showcase.validationSchema}</>}
      </p>
      <p className="text-caption text-on-surface-variant">
        every fact above was generated from the handler topic 11 wrote — open Swagger UI and find
        the same operation rendered.
      </p>
    </section>
  );
}

function HubLink({ testId, label, url }: { testId: string; label: string; url: string }) {
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

export default DocsLinkDemo;
