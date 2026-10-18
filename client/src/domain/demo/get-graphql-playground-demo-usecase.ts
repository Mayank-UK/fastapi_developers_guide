import type { Result } from '../../core/result';
import type { GraphqlPlayground, GraphqlRunResult } from './graphql-playground';
import type { GraphqlPlaygroundRepository } from './graphql-playground-repository';

/**
 * GetGraphqlPlaygroundDemoUseCase — fetches the graphql topic's console
 * package and fires rounds at the live endpoint (react-guide use-case
 * style): a thin orchestration seam over the repository port. `run` is
 * the interactive half — the operation text comes straight from the
 * editor, and a GraphQL errors array is a successful transport of a
 * failed field, so it resolves as a success carrying what the server
 * said.
 */
export class GetGraphqlPlaygroundDemoUseCase {
  private readonly repository: GraphqlPlaygroundRepository;

  constructor(repository: GraphqlPlaygroundRepository) {
    this.repository = repository;
  }

  playground(): Promise<Result<GraphqlPlayground>> {
    return this.repository.playground();
  }

  run(query: string): Promise<Result<GraphqlRunResult>> {
    return this.repository.run(query);
  }
}
