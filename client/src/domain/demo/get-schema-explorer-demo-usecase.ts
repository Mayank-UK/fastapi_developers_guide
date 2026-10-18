import type { Result } from '../../core/result';
import type { SchemaExplorer } from './schema-explorer';
import type { SchemaExplorerRepository } from './schema-explorer-repository';

/**
 * GetSchemaExplorerDemoUseCase — fetches the sql-schema topic's live
 * schema view (react-guide use-case style): a thin orchestration seam
 * over the repository port. `drill` re-fetches with a table name to add
 * the focus anatomy; the roster is the no-argument read.
 */
export class GetSchemaExplorerDemoUseCase {
  private readonly repository: SchemaExplorerRepository;

  constructor(repository: SchemaExplorerRepository) {
    this.repository = repository;
  }

  /** The roster: every public table with its fact counts. */
  roster(): Promise<Result<SchemaExplorer>> {
    return this.repository.explorer();
  }

  /** Drill into one table's full anatomy (columns, keys, checks, indexes). */
  drill(table: string): Promise<Result<SchemaExplorer>> {
    return this.repository.explorer(table);
  }
}
