/**
 * Domain models for the routing topic's explorer demo — the client-side
 * shape of GET /api/demo/routing/explorer. Field names match the server's
 * camelCase wire contract 1:1 (the DTO is the seam where wire and domain
 * may diverge later). The payload is the router's resolution replayed as
 * data: the simulated request line, the outcome (matched / 307 redirect /
 * 405 method-not-allowed / 404), the matched template with the parameters
 * it would bind, and the reasoning sentence that explains the verdict.
 */

export type ExplorerMethod =
  | 'GET'
  | 'POST'
  | 'PUT'
  | 'PATCH'
  | 'DELETE'
  | 'HEAD'
  | 'OPTIONS';

export type MatchOutcome = 'matched' | 'redirect' | 'method_not_allowed' | 'not_found';

export type ParamSource = 'path' | 'query';

export interface RequestLine {
  /** The simulated method, uppercased verb. */
  method: string;
  /** The simulated path exactly as supplied, query string included. */
  path: string;
}

export interface BoundParam {
  /** The template hole or query key the router would bind. */
  name: string;
  /** The raw value extracted from the supplied path. */
  value: string;
  /** Where the value came from: a path segment or the query string. */
  source: ParamSource;
}

export interface NearMiss {
  /** A declared path the caller probably meant. */
  path: string;
  /** The methods that near-miss path declares. */
  methods: string[];
}

export interface RoutingExplorerData {
  request: RequestLine;
  /** How many declared route templates the walk considered. */
  routeCount: number;
  outcome: MatchOutcome;
  /** One sentence explaining the verdict, server-authored. */
  reasoning: string;
  /** The template that matched; absent unless the path matched. */
  matchedPath?: string;
  /** Methods the matched template declares, uppercased and sorted. */
  matchedMethods?: string[];
  /** OpenAPI tags of the matched template. */
  matchedTags?: string[];
  /** Always present (possibly empty): parameters bound from the path. */
  pathParams: BoundParam[];
  /** Always present (possibly empty): parameters parsed from the query. */
  queryParams: BoundParam[];
  /** 405 only: the verbs the matched path actually declares. */
  allowedMethods?: string[];
  /** Redirect only: the canonical target Starlette would 307 to. */
  redirectTarget?: string;
  /** 404 only: the nearest declared paths by prefix agreement. */
  nearMisses?: NearMiss[];
}

/** What the demo component asks for: the simulated request line. */
export interface RoutingExplorerRequest {
  method: ExplorerMethod;
  path: string;
}
