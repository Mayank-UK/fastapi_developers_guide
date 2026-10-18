import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { SchemaExplorer } from '../../domain/demo/schema-explorer';
import type { SchemaExplorerRepository } from '../../domain/demo/schema-explorer-repository';
import type { SchemaExplorerApi } from './schema-explorer-api';

/**
 * SchemaExplorerRepositoryImpl — adapts the explorer API to the domain
 * port. Every thrown transport error (network, non-2xx envelope,
 * malformed payload) is guarded by safeRepositoryCall into a Failed
 * Result, so the demo component never needs try/catch and no rejection
 * goes unhandled.
 */
export class SchemaExplorerRepositoryImpl implements SchemaExplorerRepository {
  private readonly api: SchemaExplorerApi;

  constructor(api: SchemaExplorerApi) {
    this.api = api;
  }

  explorer(table?: string): Promise<Result<SchemaExplorer>> {
    return safeRepositoryCall(() => this.api.explorer(table));
  }
}
