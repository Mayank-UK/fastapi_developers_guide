import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { GraphqlPlayground, GraphqlRunResult } from '../../domain/demo/graphql-playground';
import { graphqlPlaygroundFromJson, graphqlRunResultFromJson } from './graphql-playground-dto';

/**
 * GraphqlPlaygroundApi — the transport for the graphql console: GET
 * /api/demo/api/graphql-playground (the package: endpoint, SDL, tour)
 * and POST /api/graphql (the live endpoint itself) through the shared
 * guarded fetch pipelines. The round body is the protocol's minimal
 * form — {"query": "…"} — and a 200 carrying `errors` is a SUCCESSFUL
 * transport (the not-found example relies on it); only non-2xx
 * transports (a malformed request body, a dead server) become typed
 * server failures for the error panel.
 */

const PLAYGROUND_PATH = '/demo/api/graphql-playground';
const GRAPHQL_PATH = '/graphql';

export class GraphqlPlaygroundApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fetch the playground package: the endpoint, the SDL, the tour. */
  async playground(): Promise<GraphqlPlayground> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PLAYGROUND_PATH);
      return parseDto(body, status, graphqlPlaygroundFromJson);
    });
  }

  /** Run one operation against the live GraphQL endpoint. */
  async run(query: string): Promise<GraphqlRunResult> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, GRAPHQL_PATH, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      return parseDto(body, status, graphqlRunResultFromJson);
    });
  }
}
