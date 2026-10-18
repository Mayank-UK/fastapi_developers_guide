import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ValidationArenaDemo } from './arena_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetValidationArenaDemoUseCase } from '../../../domain/demo/get-validation-arena-demo-usecase';
import type {
  ArenaModelSummary,
  ArenaRoster,
  ArenaRound,
  ArenaVerdict,
} from '../../../domain/demo/validation-arena';

/**
 * ValidationArenaDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec swaps
 * the token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * roster fetches on mount and renders the selected model's rules, the
 * editor's candidates fire verbatim under the selected model key, verdict
 * rows render accepted/coerced/rejected/absent with the exact triples,
 * model switching swaps editor and rules, invalid editor JSON is refused
 * client-side, and the 422 a non-object candidates value earns degrades
 * to the shared error panel with recovery.
 */

const noteModel: ArenaModelSummary = {
  key: 'note-create',
  model: 'NoteCreate',
  source: 'guide.domain.demos.request_methods',
  description: 'The notes playground body.',
  fields: [
    { name: 'title', rule: 'str — Field(min_length=1, max_length=80), required', required: true },
    { name: 'body', rule: "str — optional, default ''", required: false },
  ],
};

const scenarioModel: ArenaModelSummary = {
  key: 'scenario-patch',
  model: 'ScenarioPatch',
  source: 'guide.core.scenario',
  description: 'The scenario toggle body.',
  fields: [{ name: 'dataMode', rule: 'Literal["fake", "live"] — optional', required: false }],
};

const models: ArenaModelSummary[] = [noteModel, scenarioModel];

const rosterFixture: ArenaRoster = {
  models,
  reasoning: 'Three real wire models this server validates elsewhere.',
};

const rejectedFixture: ArenaVerdict = {
  model: noteModel,
  roster: models,
  rows: [
    {
      field: 'title',
      rule: 'str — Field(min_length=1, max_length=80), required',
      required: true,
      received: { type: 'str', repr: "''" },
      outcome: {
        status: 'rejected',
        loc: ['body', 'title'],
        msg: 'String should have at least 1 character',
        type: 'string_too_short',
      },
    },
    {
      field: 'body',
      rule: "str — optional, default ''",
      required: false,
      outcome: { status: 'absent', default: '' },
    },
  ],
  verdict: 'rejected',
  errors: [
    {
      loc: ['body', 'title'],
      msg: 'String should have at least 1 character',
      type: 'string_too_short',
    },
  ],
  extraKeysIgnored: [],
  reasoning: 'pydantic refused the candidates for NoteCreate.',
};

const acceptedFixture: ArenaVerdict = {
  model: scenarioModel,
  roster: models,
  rows: [
    {
      field: 'dataMode',
      rule: 'Literal["fake", "live"] — optional',
      required: false,
      received: { type: 'str', repr: "'live'" },
      outcome: { status: 'accepted', value: 'live', valueType: 'str' },
    },
  ],
  verdict: 'accepted',
  validated: { dataMode: 'live', injectFailure: null },
  extraKeysIgnored: [],
  reasoning: 'pydantic accepted the candidates for ScenarioPatch.',
};

/** Capture the rounds the component fired, answering with a fixture. */
function stubUseCase(
  respond: (round: ArenaRound) => Result<ArenaVerdict>,
  roster: Result<ArenaRoster> = success(rosterFixture),
): ArenaRound[] {
  const fired: ArenaRound[] = [];
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetValidationArenaDemoUseCase, {
    roster: () => Promise.resolve(roster),
    run: (round: ArenaRound) => {
      fired.push(round);
      return Promise.resolve(respond(round));
    },
  } as unknown as GetValidationArenaDemoUseCase);
  return fired;
}

describe('ValidationArenaDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['validation:arena']).toBeDefined();
  });

  it('fetches the roster on mount and renders the selected model rules', async () => {
    stubUseCase(() => success(acceptedFixture));

    render(<ValidationArenaDemo />);

    await waitFor(() =>
      expect(screen.getByTestId('va-rules')).toHaveTextContent('NoteCreate'),
    );
    expect(screen.getByTestId('va-rules')).toHaveTextContent('guide.domain.demos.request_methods');
    expect(screen.getByTestId('va-rules')).toHaveTextContent('title: str');
    expect(screen.getByTestId('va-idle')).toHaveTextContent('Three real wire models');
  });

  it('fires the editor candidates verbatim under the selected model key', async () => {
    const fired = stubUseCase(() => success(rejectedFixture));

    render(<ValidationArenaDemo />);
    await waitFor(() => expect(screen.getByTestId('va-rules')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('va-fire'));

    await waitFor(() => expect(screen.getByTestId('va-verdict')).toBeInTheDocument());
    expect(fired).toEqual([
      { model: 'note-create', candidates: { title: 'a note the arena judged', tags: ['arena'] } },
    ]);
  });

  it('renders rejected rows with the exact triples and the errors block', async () => {
    stubUseCase(() => success(rejectedFixture));

    render(<ValidationArenaDemo />);
    await waitFor(() => expect(screen.getByTestId('va-rules')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('va-fire'));

    await waitFor(() => expect(screen.getByTestId('va-verdict')).toBeInTheDocument());
    expect(screen.getByTestId('va-verdict')).toHaveTextContent('rejected');
    const titleRow = screen.getByTestId('va-row-title');
    expect(titleRow).toHaveTextContent('string_too_short');
    expect(titleRow).toHaveTextContent('body → title');
    expect(screen.getByTestId('va-errors')).toHaveTextContent(
      'the 422 envelope',
    );
    expect(screen.getByTestId('va-errors')).toHaveTextContent(
      'String should have at least 1 character',
    );
    expect(screen.queryByTestId('va-validated')).not.toBeInTheDocument();
  });

  it('renders accepted rows and the validated dump', async () => {
    stubUseCase(() => success(acceptedFixture));

    render(<ValidationArenaDemo />);
    await waitFor(() => expect(screen.getByTestId('va-rules')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('va-model-scenario-patch'));
    fireEvent.click(screen.getByTestId('va-fire'));

    await waitFor(() => expect(screen.getByTestId('va-verdict')).toBeInTheDocument());
    expect(screen.getByTestId('va-verdict')).toHaveTextContent('accepted');
    expect(screen.getByTestId('va-validated')).toHaveTextContent('"dataMode": "live"');
    expect(screen.getByTestId('va-row-dataMode')).toHaveTextContent('accepted');
  });

  it('switching models swaps the editor, the rules, and the presets', async () => {
    stubUseCase(() => success(acceptedFixture));

    render(<ValidationArenaDemo />);
    await waitFor(() => expect(screen.getByTestId('va-rules')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('va-model-scenario-patch'));
    const editor = screen.getByTestId('va-payload') as HTMLTextAreaElement;
    expect(editor.value).toContain('"dataMode": "live"');
    expect(screen.getByTestId('va-rules')).toHaveTextContent('ScenarioPatch');
    expect(screen.getByTestId('va-preset-literal')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('va-preset-literal'));
    expect(editor.value).toContain('"dataMode": "loud"');
  });

  it('refuses invalid editor JSON client-side without firing', async () => {
    const fired = stubUseCase(() => success(acceptedFixture));

    render(<ValidationArenaDemo />);
    await waitFor(() => expect(screen.getByTestId('va-rules')).toBeInTheDocument());

    fireEvent.change(screen.getByTestId('va-payload'), { target: { value: '{oops' } });
    fireEvent.click(screen.getByTestId('va-fire'));

    expect(screen.getByTestId('va-parse-warning')).toBeInTheDocument();
    expect(fired).toEqual([]);
  });

  it('renders the 422 a non-object candidates value earns through the error panel, with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('Request validation failed.', {
              code: 'validation_failed',
              status: 422,
              requestId: 'req-422',
            }),
          )
        : success(acceptedFixture);
    });

    render(<ValidationArenaDemo />);
    await waitFor(() => expect(screen.getByTestId('va-rules')).toBeInTheDocument());

    fireEvent.change(screen.getByTestId('va-payload'), { target: { value: '[1, 2]' } });
    fireEvent.click(screen.getByTestId('va-fire'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('validation_failed');

    // Retry re-fires the same payload and the verdict renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('va-verdict')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });

  it('renders the roster failure through the error panel', async () => {
    stubUseCase(
      () => success(acceptedFixture),
      failed(new ServerFailure('down', { code: 'service_unavailable', status: 503, requestId: 'r' })),
    );

    render(<ValidationArenaDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');
  });
});
