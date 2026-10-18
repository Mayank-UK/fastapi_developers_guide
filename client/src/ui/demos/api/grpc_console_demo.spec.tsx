import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { GrpcConsoleDemo } from './grpc_console_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetGrpcConsoleDemoUseCase } from '../../../domain/demo/get-grpc-console-demo-usecase';
import type {
  GrpcConsoleCall,
  GrpcConsoleRoster,
  GrpcConsoleRound,
} from '../../../domain/demo/grpc-console';

/**
 * GrpcConsoleDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the
 * token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * roster renders the satellite facts and the proto stanza, method chips
 * switch the argument surface, Fire POSTs the parsed call through the
 * use case (view events and notes parsed from their line editors), and
 * BOTH honest outcomes render inline — an OK round with its message
 * sequence, and a DEADLINE_EXCEEDED round with its partial messages —
 * while transport failures degrade to the shared error panel with
 * recovery. The lazy registry binds the demo id this content names.
 */

const roster: GrpcConsoleRoster = {
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
      id: 'count-views',
      name: 'CountViews',
      kind: 'client-streaming',
      input: 'stream ViewEvent',
      output: 'ViewsSummary',
      streamsIn: true,
      streamsOut: false,
      description: 'A sequence of requests, one answer.',
    },
  ],
  streamPauseMs: 50,
  reasoning: 'A real grpc.aio server is live in-process.',
};

const unaryCard = roster.methods[0];
if (unaryCard === undefined) throw new Error('fixture method card missing');

const okRound: GrpcConsoleRound = {
  method: unaryCard,
  slug: 'drafting-the-grpc-chapter',
  tag: '',
  viewEvents: 0,
  chatNotes: 0,
  sentMessages: 1,
  statusCode: 'OK',
  statusDetail: '',
  messages: [
    { index: 0, fields: { slug: 'drafting-the-grpc-chapter', title: 'Drafting the gRPC chapter' } },
  ],
  elapsedMs: 2,
  serverAddress: '127.0.0.1:53712',
  reasoning: 'A real grpc.aio call answered OK.',
};

const deadlineRound: GrpcConsoleRound = {
  method: unaryCard,
  slug: 'drafting-the-grpc-chapter',
  tag: '',
  viewEvents: 0,
  chatNotes: 0,
  deadlineMs: 120,
  sentMessages: 1,
  statusCode: 'DEADLINE_EXCEEDED',
  statusDetail: '',
  messages: [{ index: 0, fields: { slug: 'designing-urls-people-can-read' } }],
  elapsedMs: 124,
  serverAddress: '127.0.0.1:53712',
  reasoning: 'The budget died mid-stream; one message survived.',
};

type StubUseCase = {
  roster: () => Promise<Result<GrpcConsoleRoster>>;
  run: (call: GrpcConsoleCall) => Promise<Result<GrpcConsoleRound>>;
};

function stubUseCase(overrides: Partial<StubUseCase>): void {
  container.initialize(createAppConfig());
  const useCase: StubUseCase = {
    roster: async () => success(roster),
    run: async () => success(okRound),
    ...overrides,
  };
  container.register(
    ContainerTokens.GetGrpcConsoleDemoUseCase,
    useCase as unknown as GetGrpcConsoleDemoUseCase,
  );
}

describe('GrpcConsoleDemo', () => {
  it('renders the roster: satellite facts, the proto stanza, the method chips', async () => {
    stubUseCase({});

    render(<GrpcConsoleDemo />);

    expect(await screen.findByTestId('gc-roster')).toBeInTheDocument();
    expect(screen.getByTestId('gc-facts')).toHaveTextContent('guide.PostService');
    expect(screen.getByTestId('gc-facts')).toHaveTextContent('127.0.0.1:53712');
    expect(screen.getByTestId('gc-proto')).toHaveTextContent('rpc GetPost');
    const chips = screen.getAllByTestId('gc-method');
    expect(chips.map((chip) => chip.textContent)).toEqual(['GetPost · unary', 'CountViews · client-streaming']);
  });

  it('fires the unary happy path and renders the message sequence', async () => {
    stubUseCase({});

    render(<GrpcConsoleDemo />);
    await screen.findByTestId('gc-roster');

    fireEvent.click(screen.getByTestId('gc-fire'));

    const status = await screen.findByTestId('gc-status');
    expect(status).toHaveTextContent('OK');
    expect(status).toHaveTextContent('GetPost');
    expect(screen.getAllByTestId('gc-message')).toHaveLength(1);
    expect(screen.getByTestId('gc-message')).toHaveTextContent('Drafting the gRPC chapter');
    expect(screen.queryByTestId('gc-detail')).not.toBeInTheDocument();
  });

  it('renders a DEADLINE_EXCEEDED round inline with its partial message', async () => {
    stubUseCase({ run: async () => success(deadlineRound) });

    render(<GrpcConsoleDemo />);
    await screen.findByTestId('gc-roster');

    fireEvent.change(screen.getByTestId('gc-deadline'), { target: { value: '120' } });
    fireEvent.click(screen.getByTestId('gc-fire'));

    const status = await screen.findByTestId('gc-status');
    expect(status).toHaveTextContent('DEADLINE_EXCEEDED');
    expect(status).toHaveTextContent('deadline 120ms');
    expect(screen.getAllByTestId('gc-message')).toHaveLength(1);
    expect(screen.getByTestId('gc-message')).toHaveTextContent('designing-urls-people-can-read');
  });

  it('switches to the client-streaming method and parses the view-event lines', async () => {
    let seen: GrpcConsoleCall | undefined;
    stubUseCase({
      run: async (call) => {
        seen = call;
        return success(okRound);
      },
    });

    render(<GrpcConsoleDemo />);
    await screen.findByTestId('gc-roster');

    const countViewsChip = screen.getAllByTestId('gc-method')[1];
    if (countViewsChip === undefined) throw new Error('method chip missing');
    fireEvent.click(countViewsChip);
    fireEvent.change(screen.getByTestId('gc-views'), {
      target: { value: 'idempotency-retold|mak\n\nnotes-on-rfc-9457|ada\nbroken-line' },
    });
    fireEvent.click(screen.getByTestId('gc-fire'));

    await screen.findByTestId('gc-status');
    expect(seen?.method).toBe('count-views');
    expect(seen?.viewEvents).toEqual([
      { slug: 'idempotency-retold', viewer: 'mak' },
      { slug: 'notes-on-rfc-9457', viewer: 'ada' },
    ]);
    expect(seen?.deadlineMs).toBeUndefined();
  });

  it('degrades to the shared error panel on roster failure, with recovery', async () => {
    const unreachable = failed(
      new ServerFailure('The console is unreachable.', {
        code: 'service_unavailable',
        status: 503,
      }),
    );
    let rosterAnswer: Result<GrpcConsoleRoster> = unreachable;
    stubUseCase({ roster: async () => rosterAnswer });

    render(<GrpcConsoleDemo />);

    const panel = await screen.findByRole('alert');
    expect(panel).toHaveTextContent('The console is unreachable.');
    expect(panel).toHaveTextContent('service_unavailable');

    // Recovery: the retry path re-fetches the roster, which now succeeds.
    rosterAnswer = success(roster);
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    await screen.findByTestId('gc-roster');
  });

  it('is the demo the registry binds for api:grpc-console', () => {
    // The registry maps the demo id the content names to THIS component's
    // lazy chunk (demo-host.spec.tsx pins the full key list).
    expect(demoRegistry['api:grpc-console']).toBeDefined();
  });
});
