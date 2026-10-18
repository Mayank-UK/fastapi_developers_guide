import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { GraphqlPlayground, GraphqlRunResult } from '../../domain/demo/graphql-playground';
import type { GraphqlPlaygroundRepository } from '../../domain/demo/graphql-playground-repository';
import type { GraphqlPlaygroundApi } from './graphql-playground-api';

/**
 * GraphqlPlaygroundRepositoryImpl — adapts the console API to the domain
 * port. Every thrown transport error (network, non-2xx envelope,
 * malformed payload) is guarded by safeRepositoryCall into a Failed
 * Result, so the demo component never needs try/catch and no rejection
 * goes unhandled.
 */
export class GraphqlPlaygroundRepositoryImpl implements GraphqlPlaygroundRepository {
  private readonly api: GraphqlPlaygroundApi;

  constructor(api: GraphqlPlaygroundApi) {
    this.api = api;
  }

  playground(): Promise<Result<GraphqlPlayground>> {
    return safeRepositoryCall(() => this.api.playground());
  }

  run(query: string): Promise<Result<GraphqlRunResult>> {
    return safeRepositoryCall(() => this.api.run(query));
  }
}
