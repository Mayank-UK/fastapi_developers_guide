import type {
  ChatNoteInput,
  GrpcConsoleRoster,
  GrpcConsoleRound,
  GrpcMethod,
  GrpcMethodCard,
  GrpcReceivedMessage,
  GrpcStreamKind,
  ViewEventInput,
} from '../../domain/demo/grpc-console';
import {
  isRecord,
  optionalNumber,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredRecord,
  requiredString,
  requiredText,
} from '../content/validate';

/**
 * GrpcConsoleDTO — the wire/transport shapes of the gRPC console.
 * Mirrors the domain models 1:1 (the interface is the seam where wire
 * and domain may diverge); the `fromJson` builders construct ONLY the
 * listed fields (whitelist) and throw on any shape violation, which
 * parseDto upgrades to an InvalidResponseException.
 *
 * The server serializes optional facts with exclude_none, so an absent
 * `deadlineMs` is undefined here — a literal null on the wire is a drift
 * and fails validation loudly. Message `fields` are protobuf field maps
 * (proto names, snake_case, defaults included) and stay opaque records
 * by design: the console renders them, it does not interpret them.
 */

export type GrpcConsoleRosterDto = GrpcConsoleRoster;
export type GrpcConsoleRoundDto = GrpcConsoleRound;

const METHODS: readonly GrpcMethod[] = ['get-post', 'stream-posts', 'count-views', 'echo-chat'];
const KINDS: readonly GrpcStreamKind[] = [
  'unary',
  'server-streaming',
  'client-streaming',
  'bidirectional',
];

function oneOf<T extends string>(value: unknown, allowed: readonly T[], what: string): T {
  if (typeof value === 'string' && (allowed as readonly string[]).includes(value)) {
    return value as T;
  }
  throw new Error(`expected one of [${allowed.join(', ')}] at "${what}"`);
}

function methodCardFromJson(body: unknown): GrpcMethodCard {
  if (!isRecord(body)) throw new Error('method card must be an object');
  return {
    id: oneOf(body.id, METHODS, 'methods.id'),
    name: requiredString(body, 'name'),
    kind: oneOf(body.kind, KINDS, 'methods.kind'),
    input: requiredString(body, 'input'),
    output: requiredString(body, 'output'),
    streamsIn: requiredBoolean(body, 'streamsIn'),
    streamsOut: requiredBoolean(body, 'streamsOut'),
    description: requiredString(body, 'description'),
  };
}

/** Deserialize + validate the roster. */
export function grpcConsoleRosterFromJson(body: unknown): GrpcConsoleRosterDto {
  if (!isRecord(body)) throw new Error('grpc roster must be an object');
  return {
    serverAddress: requiredString(body, 'serverAddress'),
    service: requiredString(body, 'service'),
    protoExcerpt: requiredString(body, 'protoExcerpt'),
    methods: requiredArray(body, 'methods').map(methodCardFromJson),
    streamPauseMs: requiredNumber(body, 'streamPauseMs'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

function receivedFromJson(body: unknown): GrpcReceivedMessage {
  if (!isRecord(body)) throw new Error('received message must be an object');
  const fields = requiredRecord(body, 'fields');
  for (const value of Object.values(fields)) {
    if (value === null || typeof value === 'function') {
      throw new Error('expected a JSON value at "fields[]"');
    }
  }
  return {
    index: requiredNumber(body, 'index'),
    fields,
  };
}

/** Deserialize + validate one finished round. */
export function grpcConsoleRoundFromJson(body: unknown): GrpcConsoleRoundDto {
  if (!isRecord(body)) throw new Error('grpc round must be an object');
  const deadlineMs = optionalNumber(body, 'deadlineMs');
  return {
    method: methodCardFromJson(requiredRecord(body, 'method')),
    slug: requiredString(body, 'slug'),
    tag: requiredText(body, 'tag'),
    viewEvents: requiredNumber(body, 'viewEvents'),
    chatNotes: requiredNumber(body, 'chatNotes'),
    ...(deadlineMs === undefined ? {} : { deadlineMs }),
    sentMessages: requiredNumber(body, 'sentMessages'),
    statusCode: requiredString(body, 'statusCode'),
    statusDetail: requiredText(body, 'statusDetail'),
    messages: requiredArray(body, 'messages').map(receivedFromJson),
    elapsedMs: requiredNumber(body, 'elapsedMs'),
    serverAddress: requiredString(body, 'serverAddress'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Serialize one console call for the wire — omitting the empty options. */
export function grpcConsoleCallToJson(call: {
  method: GrpcMethod;
  slug: string;
  tag: string;
  viewEvents: readonly ViewEventInput[];
  chatNotes: readonly ChatNoteInput[];
  deadlineMs?: number;
}): Record<string, unknown> {
  return {
    method: call.method,
    slug: call.slug,
    tag: call.tag,
    viewEvents: call.viewEvents.map((event) => ({ slug: event.slug, viewer: event.viewer })),
    chatNotes: call.chatNotes.map((note) => ({ sender: note.sender, text: note.text })),
    ...(call.deadlineMs === undefined ? {} : { deadlineMs: call.deadlineMs }),
  };
}
