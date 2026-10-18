import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { GrpcConsoleApi } from './grpc-console-api';
import { GrpcConsoleRepositoryImpl } from './grpc-console-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * GrpcConsoleRepositoryImpl spec — fixture-driven, one endpoint at a
 * time: the roster round-trips the satellite address + the four methods
 * with their stream kinds, a run POSTs the console call shape (method +
 * arguments + optional deadlineMs omitted when unset) and parses the
 * round INCLUDING the honest failure payloads (a NOT_FOUND or
 * DEADLINE_EXCEEDED round is a SUCCESSFUL transport — the status is the
 * answer), while network faults and malformed payloads resolve as
 * Failed Results, never throws.
 */

const CONSOLE_URL = '/api/demo/api/grpc-console';

const rosterPayload = {
  serverAddress: '127.0.0.1:53712',
  service: 'guide.PostService',
  protoExcerpt: 'service PostService {\n  rpc GetPost(GetPostRequest) returns (PostReply);\n}',
  methods: [
    {
      id: 'get-post',
      name: 'GetPost',
      kind: 'unary',
      input: 'GetPostRequest',
      output: 'PostReply',
      streamsIn: false,
      streamsOut: false,
      description: 'One request, one answer.',
    },
    {
      id: 'echo-chat',
      name: 'EchoChat',
      kind: 'bidirectional',
      input: 'stream ChatNote',
      output: 'stream ChatNote',
      streamsIn: true,
      streamsOut: true,
      description: 'Streams both ways.',
    },
  ],
  streamPauseMs: 50,
  reasoning: 'A real grpc.aio server is live in-process.',
};

const roundPayload = {
  method: rosterPayload.methods[0],
  slug: 'no-such-post',
  tag: '',
  viewEvents: 0,
  chatNotes: 0,
  sentMessages: 1,
  statusCode: 'NOT_FOUND',
  statusDetail: "Post 'no-such-post' not found",
  messages: [],
  elapsedMs: 2,
  serverAddress: '127.0.0.1:53712',
  reasoning: "A real grpc.aio call to 127.0.0.1:53712 answered NOT_FOUND (0 message(s), 2ms elapsed).",
};

const deadlinePayload = {
  ...roundPayload,
  method: rosterPayload.methods[1],
  statusCode: 'DEADLINE_EXCEEDED',
  statusDetail: '',
  deadlineMs: 120,
  messages: [
    { index: 0, fields: { slug: 'designing-urls-people-can-read', title: 'Designing URLs people can read' } },
  ],
  elapsedMs: 124,
};

function makeRepository(): GrpcConsoleRepositoryImpl {
  return new GrpcConsoleRepositoryImpl(new GrpcConsoleApi(createAppConfig()));
}

describe('GrpcConsoleRepositoryImpl', () => {
  it('fetches and parses the roster', async () => {
    stubApiFetch([{ url: CONSOLE_URL, method: 'GET', body: rosterPayload }]);

    const result = await makeRepository().roster();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.serverAddress).toBe('127.0.0.1:53712');
      expect(result.value.methods.map((method) => [method.id, method.kind])).toEqual([
        ['get-post', 'unary'],
        ['echo-chat', 'bidirectional'],
      ]);
      expect(result.value.methods[1]?.streamsIn).toBe(true);
      expect(result.value.streamPauseMs).toBe(50);
    }
  });

  it('runs a round and parses an honest NOT_FOUND as a successful transport', async () => {
    stubApiFetch([{ url: CONSOLE_URL, method: 'POST', body: roundPayload }]);

    const result = await makeRepository().run({
      method: 'get-post',
      slug: 'no-such-post',
      tag: '',
      viewEvents: [],
      chatNotes: [],
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.statusCode).toBe('NOT_FOUND');
      expect(result.value.statusDetail).toContain('not found');
      expect(result.value.messages).toEqual([]);
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe('{"method":"get-post","slug":"no-such-post","tag":"","viewEvents":[],"chatNotes":[]}');
  });

  it('parses a mid-stream deadline round with its partial messages and deadlineMs', async () => {
    stubApiFetch([{ url: CONSOLE_URL, method: 'POST', body: deadlinePayload }]);

    const result = await makeRepository().run({
      method: 'echo-chat',
      slug: '',
      tag: '',
      viewEvents: [],
      chatNotes: [],
      deadlineMs: 120,
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.statusCode).toBe('DEADLINE_EXCEEDED');
      expect(result.value.deadlineMs).toBe(120);
      const [first] = result.value.messages;
      expect(first?.fields['slug']).toBe('designing-urls-people-can-read');
    }
    const init = vi.mocked(fetch).mock.calls[0]?.[1];
    expect(init?.body).toContain('"deadlineMs":120');
  });

  it('rejects a payload with a null deadline (exclude_none contract)', async () => {
    stubApiFetch([
      { url: CONSOLE_URL, method: 'POST', body: { ...roundPayload, deadlineMs: null } },
    ]);

    const result = await makeRepository().run({
      method: 'get-post',
      slug: 'x',
      tag: '',
      viewEvents: [],
      chatNotes: [],
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('rejects a malformed roster (bad stream kind)', async () => {
    stubApiFetch([
      {
        url: CONSOLE_URL,
        method: 'GET',
        body: { ...rosterPayload, methods: [{ ...rosterPayload.methods[0], kind: 'triangular' }] },
      },
    ]);

    const result = await makeRepository().roster();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network fault into a Failed Result', async () => {
    stubNetworkFailure();

    const result = await makeRepository().roster();

    expect(result.ok).toBe(false);
  });
});
