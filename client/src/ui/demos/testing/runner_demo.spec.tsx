import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { TestingRunnerDemo } from './runner_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetTestingRunnerDemoUseCase } from '../../../domain/demo/get-testing-runner-demo-usecase';
import type {
  SliceRunResult,
  TestingRunnerData,
} from '../../../domain/demo/testing-runner';

/**
 * TestingRunnerDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration (the container's documented
 * replace-a-singleton seam) instead of stubbing fetch. Behavior, not
 * implementation: the roster renders the four slices with the recipe
 * row and the guard facts, a run click fires exactly one run and
 * renders the genuine-looking result card, the pending row shows while
 * a run is in flight, and both roster and run failures degrade to the
 * shared error panel with recovery.
 */

const roster: TestingRunnerData = {
  slices: [
    {
      sliceId: 'unit-pure',
      title: 'Pure unit tests',
      focus: 'Topic 14 HMAC machinery: pure domain functions.',
      paths: ['server/tests/domain/test_webhook_signing.py'],
      note: 'The pyramid base — fast and deterministic.',
    },
    {
      sliceId: 'testcontainers-skips',
      title: 'Testcontainers (honest skips)',
      focus: 'The clean-database round-trip.',
      paths: ['server/tests/data/test_orm_testcontainers.py'],
      note: 'No docker.sock here: every test skips with the reason.',
    },
  ],
  clientRecipe: {
    title: "The client's vitest suite (a recipe, not a run)",
    command: "docker exec fastapi_developers_guide_client_dev bash -lc 'cd /app && npm test'",
    note: 'The server cannot run the client suite — the command is the honesty.',
  },
  facts: {
    commandTemplate: '<venv python> -m pytest -v --no-header <slice paths>',
    cwd: 'server/',
    timeoutSeconds: 90,
    offLoop: 'asyncio.to_thread (a blocking subprocess never sits on the event loop)',
    guardEnv: 'FDG_TEST_RUNNER_CHILD',
  },
  reasoning: 'The panel never fakes a run it did not make.',
};

const runResult: SliceRunResult = {
  sliceId: 'unit-pure',
  outcome: 'passed',
  passed: 14,
  failed: 0,
  skipped: 0,
  errors: 0,
  durationMs: 1834.2,
  pytestSeconds: 0.02,
  summaryLine: '14 passed, 1 warning in 0.02s',
  commandLine:
    '/venv/bin/python -m pytest -v --no-header tests/domain/test_webhook_signing.py',
  testLines: [
    {
      nodeid: 'tests/domain/test_webhook_signing.py::test_signed_headers_round_trip_verifies',
      outcome: 'passed',
    },
    {
      nodeid: 'tests/domain/test_webhook_signing.py::test_signature_scheme_is_v1_prefixed_hex_sha256',
      outcome: 'passed',
    },
  ],
  note: 'The pyramid base — fast and deterministic.',
};

/** A controllable promise: the test releases the run when it chooses. */
interface Deferred {
  promise: Promise<Result<SliceRunResult>>;
  resolve: (value: Result<SliceRunResult>) => void;
}

function makeDeferred(): Deferred {
  let resolve!: (value: Result<SliceRunResult>) => void;
  const promise = new Promise<Result<SliceRunResult>>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

/** Swap the container's use-case token for a stub answering the pair. */
function stubUseCase(
  respondRoster: () => Result<TestingRunnerData>,
  respondRun: (sliceId: string) => Result<SliceRunResult> | Promise<Result<SliceRunResult>>,
): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetTestingRunnerDemoUseCase, {
    execute: () => Promise.resolve(respondRoster()),
    run: (sliceId: string) => Promise.resolve(respondRun(sliceId)),
  } as unknown as GetTestingRunnerDemoUseCase);
}

describe('TestingRunnerDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['testing:runner']).toBeDefined();
  });

  it('renders the roster: slices, recipe row, guard facts, reasoning', async () => {
    stubUseCase(() => success(roster), () => success(runResult));

    render(<TestingRunnerDemo />);

    await waitFor(() => expect(screen.getByTestId('tr-slice-unit-pure')).toBeInTheDocument());
    expect(screen.getByTestId('tr-slice-unit-pure')).toHaveTextContent('test_webhook_signing.py');
    expect(screen.getByTestId('tr-slice-testcontainers-skips')).toHaveTextContent(
      'test_orm_testcontainers.py',
    );
    expect(screen.getByTestId('tr-recipe')).toHaveTextContent('npm test');
    expect(screen.getByTestId('tr-recipe')).toHaveTextContent('recipe, not a run');
    expect(screen.getByTestId('tr-facts')).toHaveTextContent('FDG_TEST_RUNNER_CHILD');
    expect(screen.getByTestId('tr-facts')).toHaveTextContent('asyncio.to_thread');
    expect(screen.getByTestId('tr-reasoning')).toHaveTextContent('never fakes a run');
  });

  it('fires exactly one run per click and renders the genuine result card', async () => {
    let runs = 0;
    stubUseCase(
      () => success(roster),
      (sliceId) => {
        runs += 1;
        expect(sliceId).toBe('unit-pure');
        return success(runResult);
      },
    );

    render(<TestingRunnerDemo />);
    await waitFor(() => expect(screen.getByTestId('tr-run-unit-pure')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('tr-run-unit-pure'));

    await waitFor(() =>
      expect(screen.getByTestId('tr-result-unit-pure')).toBeInTheDocument(),
    );
    expect(runs).toBe(1);
    const card = screen.getByTestId('tr-result-unit-pure');
    expect(card).toHaveTextContent('passed');
    expect(card).toHaveTextContent('passed 14');
    expect(card).toHaveTextContent('skipped 0');
    expect(card).toHaveTextContent('wall 1834.2ms');
    expect(card).toHaveTextContent('14 passed, 1 warning in 0.02s');
    expect(card).toHaveTextContent('test_signed_headers_round_trip_verifies');
  });

  it('shows the pending row while a run is in flight', async () => {
    const gate = makeDeferred();
    stubUseCase(
      () => success(roster),
      () => gate.promise,
    );

    render(<TestingRunnerDemo />);
    await waitFor(() => expect(screen.getByTestId('tr-run-unit-pure')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('tr-run-unit-pure'));

    await waitFor(() =>
      expect(screen.getByTestId('tr-pending-unit-pure')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('tr-run-unit-pure')).toBeDisabled();

    gate.resolve(success(runResult));
    await waitFor(() =>
      expect(screen.getByTestId('tr-result-unit-pure')).toBeInTheDocument(),
    );
  });

  it('degrades the roster to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(
      () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('The roster did not answer.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-7',
              }),
            )
          : success(roster);
      },
      () => success(runResult),
    );

    render(<TestingRunnerDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('tr-slice-unit-pure')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });

  it('degrades a failed run to the shared error panel with a retry that works', async () => {
    let calls = 0;
    stubUseCase(
      () => success(roster),
      () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Unknown test slice.', {
                code: 'not_found',
                status: 404,
                requestId: 'req-8',
              }),
            )
          : success(runResult);
      },
    );

    render(<TestingRunnerDemo />);
    await waitFor(() => expect(screen.getByTestId('tr-run-unit-pure')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('tr-run-unit-pure'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('not_found');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('tr-result-unit-pure')).toBeInTheDocument(),
    );
    expect(calls).toBe(2);
  });
});
