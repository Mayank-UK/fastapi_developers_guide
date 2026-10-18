import type { Result } from '../../core/result';
import type { DocsHub } from './docs-link';

/**
 * DocsLinkRepository — the domain-facing port for the api-documentation
 * topic's hub demo. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 * One method, one endpoint: the hub payload is observational — the
 * server reports the running app's generated documentation as it stands.
 */
export interface DocsLinkRepository {
  /** Fetch the documentation hub: links, counts, areas, the schema slice. */
  hub(): Promise<Result<DocsHub>>;
}
