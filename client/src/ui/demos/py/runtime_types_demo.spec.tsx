import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RuntimeTypesDemo } from './runtime_types_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetRuntimeTypesDemoUseCase } from '../../../domain/demo/get-runtime-types-demo-usecase';
import type { RuntimeTypesDemoData } from '../../../domain/demo/runtime-types';

/**
 * RuntimeTypesDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam) instead
 * of stubbing fetch. Behavior, not implementation: the four payload faces
 * render, the wrong-typed call's returned value is displayed as the proof,
 * and failures degrade to the shared error panel with recovery.
 */

const fixture: RuntimeTypesDemoData = {
  hintsVsRaw: [
    {
      symbol: 'guide.domain.demos.runtime_types.repeat',
      mode: 'deferred',
      rows: [
        { name: 'text', raw: "'str'", resolved: 'str' },
        { name: 'return', raw: "'str'", resolved: 'str' },
      ],
    },
    {
      symbol: 'guide.content.registry.ContentRegistry.topic_by_id',
      mode: 'eager',
      rows: [{ name: 'return', raw: 'Topic | None', resolved: 'Topic | None' }],
    },
  ],
  originArgs: [
    { symbol: 'list[int]', alias: 'list[int]', origin: 'list', args: ['int'] },
    {
      symbol: 'ContentRegistry.topic_by_id (return)',
      alias: 'Topic | None',
      origin: 'UnionType',
      args: ['Topic', 'None'],
    },
  ],
  faceOff: {
    dataclassSymbol: 'guide.content.snippet_matcher.SnippetMatch',
    dataclassFields: [
      { name: 'ok', annotation: 'bool', required: true },
      { name: 'reason', annotation: 'str | None', required: false },
    ],
    pydanticSymbol: 'guide.content.models.Topic',
    pydanticFields: [
      { name: 'id', annotation: 'str', required: true },
      { name: 'subtitle', annotation: 'str | None', required: false },
    ],
  },
  enforcement: {
    function: 'repeat',
    signature: 'def repeat(text: str, times: int) -> str',
    call: 'repeat(3.0, 2)',
    declaredReturn: 'str',
    actualReturn: 'float',
    returnedValue: '6.0',
    mypyVerdict:
      'Argument 1 to "repeat" has incompatible type "float"; expected "str"',
  },
  boundary: {
    model: 'Topic',
    badInput: '{"id": 123, …}',
    outcome: 'rejected',
    errorType: 'string_type',
    message: 'Input should be a valid string',
  },
};

function stubUseCase(execute: () => Promise<Result<RuntimeTypesDemoData>>): void {
  container.initialize(createAppConfig());
  container.register(
    ContainerTokens.GetRuntimeTypesDemoUseCase,
    { execute } as unknown as GetRuntimeTypesDemoUseCase,
  );
}

describe('RuntimeTypesDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['py:runtime-types']).toBeDefined();
  });

  it('renders loading first, then all four payload faces', async () => {
    stubUseCase(async () => success(fixture));

    render(<RuntimeTypesDemo />);

    expect(screen.getByTestId('runtime-types-loading')).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByTestId('rt-hints')).toBeInTheDocument(),
    );

    // Hints-vs-raw: both symbols, raw quoted strings vs resolved types.
    expect(screen.getByText('guide.domain.demos.runtime_types.repeat')).toBeInTheDocument();
    expect(screen.getAllByText("'str'").length).toBeGreaterThan(0);
    expect(screen.getAllByText('Topic | None').length).toBeGreaterThan(0);

    // Origins: origin column carries list / UnionType.
    expect(screen.getByTestId('rt-origins')).toHaveTextContent('UnionType');

    // Face-off: both models side by side with requiredness.
    expect(screen.getByTestId('rt-faceoff-dataclass')).toHaveTextContent('SnippetMatch');
    expect(screen.getByTestId('rt-faceoff-pydantic')).toHaveTextContent('str | None');
    expect(screen.getByTestId('rt-faceoff-dataclass')).toHaveTextContent('has default');

    // The enforcement proof is displayed as the thing it is.
    expect(screen.getByTestId('rt-returned-value')).toHaveTextContent('6.0');
    expect(screen.getByTestId('rt-enforcement')).toHaveTextContent('float');

    // The boundary check names the library that did reject.
    expect(screen.getByTestId('rt-boundary')).toHaveTextContent('string_type');
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The demo endpoint is down.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-31',
            }),
          )
        : success(fixture);
    });

    render(<RuntimeTypesDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    // Retry re-runs the use case and the payload renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('rt-hints')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
