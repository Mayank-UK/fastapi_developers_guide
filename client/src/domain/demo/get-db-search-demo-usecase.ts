import type { Result } from '../../core/result';
import type { SearchDemo } from './db-search';
import type { DbSearchRepository } from './db-search-repository';

/**
 * GetDbSearchDemoUseCase — fetches the databases-sql topic's search lab
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. `run` searches; any input dissolves safely into
 * lexemes (plainto_tsquery), so free text is welcome.
 */
export class GetDbSearchDemoUseCase {
  private readonly repository: DbSearchRepository;

  constructor(repository: DbSearchRepository) {
    this.repository = repository;
  }

  /** Rank full-text matches for one query. */
  run(q?: string): Promise<Result<SearchDemo>> {
    return this.repository.search(q);
  }
}
