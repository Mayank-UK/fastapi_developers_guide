/**
 * Domain models for the http-web topic's headers-echo demo — the
 * client-side shape of GET/POST /api/demo/http/headers. Field names match
 * the server's camelCase wire contract 1:1 (the DTO is the seam where wire
 * and domain may diverge later). The payload is what the server actually
 * received on YOUR request: request line, content type, selected headers
 * each classified end-to-end vs hop-by-hop, and the RFC 9110 reference
 * list.
 */

export type HeaderScope = 'end-to-end' | 'hop-by-hop';

export interface EchoedHeader {
  /** Lowercase header name, exactly as the server received it. */
  name: string;
  /** The header's value, unmodified. */
  value: string;
  /** End-to-end headers survive proxies; hop-by-hop belong to one transport. */
  scope: HeaderScope;
  /** One-line teaching note for known headers; absent when there is none. */
  note?: string;
}

export interface HttpHeadersEchoData {
  method: string;
  path: string;
  /** The raw query string; absent when the request carried none. */
  query?: string;
  /** The request's content type; absent for bodyless requests. */
  contentType?: string;
  /** The parsed POST body message; absent unless the POST carried one. */
  bodyMessage?: string;
  headers: EchoedHeader[];
  /** The RFC 9110 §7.6.1 hop-by-hop list, for reference beside the echo. */
  hopByHop: string[];
}

/** What the demo component asks for: how to fire the request. */
export interface HttpHeadersDemoRequest {
  method: 'GET' | 'POST';
  /** Optional custom header (e.g. x-demo-trace) — an end-to-end proof. */
  headerName?: string;
  headerValue?: string;
  /** POST only: a message body the server parses and echoes back. */
  message?: string;
}
