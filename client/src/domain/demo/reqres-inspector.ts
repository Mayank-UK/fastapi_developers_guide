/**
 * Domain models for the request-response topic's inspector demo — the
 * client-side shape of GET/POST /api/demo/reqres/inspector. Field names
 * match the server's camelCase wire contract 1:1 (the DTO is the seam
 * where wire and domain may diverge later). The payload is the handler's
 * own view of the request that fetched it: the request line, the query
 * parsed with every occurrence preserved (repeated keys flagged — the
 * multi-value behavior a list[str] handler binds), a selected view of the
 * headers, the POST body contract, the client address the transport
 * reported, and the request id the middleware assigned on the way in.
 */

export interface QueryParamView {
  /** The query key as parsed (percent-decoded by the server). */
  name: string;
  /** Every value sent for the key, in arrival order. */
  values: string[];
  /** True when the key appeared more than once (?tag=a&tag=b). */
  isRepeated: boolean;
}

export interface SeenHeader {
  /** Header name, lowercased as the server reports it. */
  name: string;
  /** The header value exactly as received. */
  value: string;
}

export interface ClientAddress {
  /** The peer host the transport reported (e.g. "127.0.0.1"). */
  host: string;
  /** The peer port. */
  port: number;
}

export interface RequestInspectorData {
  method: string;
  path: string;
  /** The raw query string; absent when the URL carried none. */
  rawQuery?: string;
  /** Always present (possibly empty): the parsed query view. */
  queryParams: QueryParamView[];
  /** Always present (possibly empty): the selected header view. */
  headers: SeenHeader[];
  contentType?: string;
  contentLength?: number;
  bodyMessage?: string;
  client?: ClientAddress;
  /** The id the real request-id middleware assigned to this very request. */
  requestId: string;
  requestIdHeader: string;
  /** One paragraph explaining the reflection, server-authored. */
  reasoning: string;
}

/** What the demo component sends: the probe the server will reflect. */
export interface InspectorProbe {
  method: 'GET' | 'POST';
  /** The query string to attach (without the leading ?); may be empty. */
  query: string;
  /** An optional custom header to send along (name + value). */
  headerName?: string;
  headerValue?: string;
  /** POST only: the JSON body's message field. */
  bodyMessage?: string;
}
