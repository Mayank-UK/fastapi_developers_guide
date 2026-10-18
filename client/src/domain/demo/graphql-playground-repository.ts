import type { Result } from '../../core/result';
import type { GraphqlPlayground, GraphqlRunResult } from './graphql-playground';

/**
 * GraphqlPlaygroundRepository — the domain-facing port for the graphql
 * topic's console demo. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root. Two methods, two endpoints: the package is observational (the
 * server serves the live SDL + tour), while `run` POSTs an operation to
 * the REAL /api/graphql — a GraphQL response with `errors` is a valid
 * result, not a failure, so it travels inside a successful Result.
 */
export interface GraphqlPlaygroundRepository {
  /** Fetch the playground package: the endpoint, the SDL, the tour. */
  playground(): Promise<Result<GraphqlPlayground>>;

  /** Run one operation against the live GraphQL endpoint. */
  run(query: string): Promise<Result<GraphqlRunResult>>;
}
