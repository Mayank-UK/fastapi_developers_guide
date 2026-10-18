import type { Result } from '../../core/result';
import type { DocsLinkRepository } from './docs-link-repository';
import type { DocsHub } from './docs-link';

/**
 * GetDocsLinkDemoUseCase — fetches the api-documentation topic's hub
 * payload (react-guide use-case style): a thin orchestration seam over
 * the repository port. Carries no parameters — the demo is
 * observational; the server introspects the same OpenAPI document the
 * docs UIs render.
 */
export class GetDocsLinkDemoUseCase {
  private readonly repository: DocsLinkRepository;

  constructor(repository: DocsLinkRepository) {
    this.repository = repository;
  }

  hub(): Promise<Result<DocsHub>> {
    return this.repository.hub();
  }
}
