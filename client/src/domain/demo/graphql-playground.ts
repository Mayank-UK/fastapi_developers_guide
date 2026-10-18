/**
 * Domain models for the graphql topic's playground (demo block id
 * `api:graphql-playground`) — the client-side shape of
 * GET /api/demo/api/graphql-playground plus the result contract of the
 * console's live rounds against POST /api/graphql. Field names match the
 * server's camelCase wire contract 1:1.
 *
 * The payload packages the running schema's real SDL with a curated tour
 * of five operations; the console loads any example into its editor and
 * fires it at the live endpoint, whose GraphQL response carries data
 * and/or errors per the GraphQL over HTTP spec — both shapes are honest
 * outcomes here (the not-found example deliberately returns errors).
 */

/** One curated operation the console can load into its editor. */
export interface GraphqlExample {
  id: string;
  label: string;
  description: string;
  query: string;
}

/** The playground package: where the API lives + the schema + the tour. */
export interface GraphqlPlayground {
  endpoint: string;
  sdl: string;
  examples: GraphqlExample[];
  reasoning: string;
}

/** One entry of a GraphQL response's errors array (spec shape). */
export interface GraphqlError {
  message: string;
  locations?: readonly GraphqlErrorLocation[];
  path?: readonly (string | number)[];
  extensions?: Readonly<Record<string, unknown>>;
}

/** The line/column pair GraphQL errors carry for query positions. */
export interface GraphqlErrorLocation {
  line: number;
  column: number;
}

/**
 * The result of one console round: the GraphQL spec allows data,
 * errors, or both — a 200 with `errors` is a successful transport of a
 * failed field, so both arrive as success and the console renders what
 * the server said.
 */
export interface GraphqlRunResult {
  data?: Readonly<Record<string, unknown>>;
  errors?: readonly GraphqlError[];
}
