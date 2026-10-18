/**
 * Domain models for the gRPC topic's console (demo block id
 * `api:grpc-console`) — the client-side shape of the console endpoints.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The console is a caller's seat over the REAL in-process gRPC
 * satellite: the roster names the live address, the service stanza of
 * the real guide.proto, and the four methods with their stream kinds;
 * a run performs one REAL grpc.aio round (method + arguments + optional
 * deadline) and reports the response messages in arrival order (proto
 * field names preserved inside `fields`), the status code in grpc's own
 * vocabulary, and elapsed milliseconds. `deadlineMs` is optional here
 * because the server serializes it with exclude_none — a null on the
 * wire would be a drift.
 */

/** The console's method roster — one per stream kind the contract defines. */
export type GrpcMethod = 'get-post' | 'stream-posts' | 'count-views' | 'echo-chat';

/** The four RPC shapes: the vocabulary §3 of the topic teaches. */
export type GrpcStreamKind = 'unary' | 'server-streaming' | 'client-streaming' | 'bidirectional';

/** One client-streaming view event: a viewer looked at a post. */
export interface ViewEventInput {
  slug: string;
  viewer: string;
}

/** One bidirectional chat note; the service echoes it back. */
export interface ChatNoteInput {
  sender: string;
  text: string;
}

/** One method as the roster offers it: name, stream kind, message types. */
export interface GrpcMethodCard {
  id: GrpcMethod;
  name: string;
  kind: GrpcStreamKind;
  input: string;
  output: string;
  streamsIn: boolean;
  streamsOut: boolean;
  description: string;
}

/** Wire shape of GET /api/demo/api/grpc-console. */
export interface GrpcConsoleRoster {
  serverAddress: string;
  service: string;
  protoExcerpt: string;
  methods: readonly GrpcMethodCard[];
  streamPauseMs: number;
  reasoning: string;
}

/** One console round the demo fires: method, arguments, optional deadline. */
export interface GrpcConsoleCall {
  method: GrpcMethod;
  slug: string;
  tag: string;
  viewEvents: readonly ViewEventInput[];
  chatNotes: readonly ChatNoteInput[];
  deadlineMs?: number;
}

/** One message that came back, in arrival order (proto field names kept). */
export interface GrpcReceivedMessage {
  index: number;
  fields: Readonly<Record<string, unknown>>;
}

/** Wire shape of POST /api/demo/api/grpc-console — one real round. */
export interface GrpcConsoleRound {
  method: GrpcMethodCard;
  slug: string;
  tag: string;
  viewEvents: number;
  chatNotes: number;
  deadlineMs?: number;
  sentMessages: number;
  statusCode: string;
  statusDetail: string;
  messages: readonly GrpcReceivedMessage[];
  elapsedMs: number;
  serverAddress: string;
  reasoning: string;
}
