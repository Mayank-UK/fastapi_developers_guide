import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PydLabDemo } from './lab_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetPydLabDemoUseCase } from '../../../domain/demo/get-pyd-lab-demo-usecase';
import type {
  PydLabReportData,
  PydLabSchemaData,
} from '../../../domain/demo/pyd-lab';

/**
 * PydLabDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the schema
 * fetches on mount, the editor's payload fires verbatim, the per-field
 * report table renders clean/coerced/rejected rows, the specimen verdict
 * carries both outcomes, invalid editor JSON is refused client-side, and
 * the 422 a refused body earns degrades to the shared error panel.
 */

const schemaFixture: PydLabSchemaData = {
  model: 'LabSpecimen',
  jsonSchema: {
    title: 'LabSpecimen',
    required: ['count', 'flag', 'tags', 'score', 'handle'],
    properties: {
      score: { title: 'Score', type: 'integer', maximum: 100, minimum: 1 },
    },
  },
};

const reportFixture: PydLabReportData = {
  rows: [
    {
      field: 'count',
      rule: 'int — numeric strings and whole floats coerce, lax mode',
      received: { type: 'str', repr: "'42'" },
      outcome: { status: 'coerced', value: 42, valueType: 'int', fromType: 'str' },
    },
    {
      field: 'flag',
      rule: 'bool',
      received: { type: 'str', repr: "'true'" },
      outcome: { status: 'coerced', value: true, valueType: 'bool', fromType: 'str' },
    },
    {
      field: 'tags',
      rule: 'list[str]',
      received: { type: 'list', repr: "['boundary', 'types']" },
      outcome: { status: 'clean', value: ['boundary', 'types'], valueType: 'list' },
    },
    {
      field: 'score',
      rule: 'int, Field(ge=1, le=100)',
      received: { type: 'str', repr: "'100'" },
      outcome: { status: 'coerced', value: 100, valueType: 'int', fromType: 'str' },
    },
    {
      field: 'handle',
      rule: 'str + @field_validator',
      received: { type: 'str', repr: "'  Grace Hopper '" },
      outcome: { status: 'coerced', value: 'grace-hopper', valueType: 'str', fromType: 'str' },
    },
  ],
  specimenValid: true,
  specimen: {
    count: 42,
    flag: true,
    tags: ['boundary', 'types'],
    score: 100,
    handle: 'grace-hopper',
  },
};

const rejectedFixture: PydLabReportData = {
  rows: [
    {
      field: 'score',
      rule: 'int, Field(ge=1, le=100)',
      received: { type: 'int', repr: '0' },
      outcome: {
        status: 'rejected',
        errorType: 'greater_than_equal',
        message: 'Input should be greater than or equal to 1',
      },
    },
  ],
  specimenValid: false,
  specimenErrors: [
    { loc: ['score'], msg: 'Input should be greater than or equal to 1', type: 'greater_than_equal' },
  ],
};

/** Capture the payloads the component fired, answering with a fixture. */
function stubUseCase(
  respond: (payload: unknown) => Result<PydLabReportData>,
  schema: Result<PydLabSchemaData> = success(schemaFixture),
): unknown[] {
  const fired: unknown[] = [];
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetPydLabDemoUseCase, {
    schema: () => Promise.resolve(schema),
    validate: (payload: unknown) => {
      fired.push(payload);
      return Promise.resolve(respond(payload));
    },
  } as unknown as GetPydLabDemoUseCase);
  return fired;
}

describe('PydLabDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['pyd:lab']).toBeDefined();
  });

  it('starts idle, fetches the schema on mount, and fires the editor verbatim', async () => {
    const fired = stubUseCase(() => success(reportFixture));

    render(<PydLabDemo />);

    expect(screen.getByTestId('pyd-idle')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId('pyd-schema')).toHaveTextContent('LabSpecimen'),
    );
    expect(screen.getByTestId('pyd-schema')).toHaveTextContent('"minimum": 1');

    fireEvent.click(screen.getByTestId('pyd-fire'));

    await waitFor(() => expect(screen.getByTestId('pyd-table')).toBeInTheDocument());
    // The prefilled coercion payload went over the seam exactly as edited.
    expect(fired).toEqual([
      {
        count: '42',
        flag: 'true',
        tags: ['boundary', 'types'],
        score: '100',
        handle: '  Grace Hopper ',
      },
    ]);

    const countRow = screen.getByTestId('pyd-row-count');
    expect(countRow).toHaveTextContent("str '42'");
    expect(countRow).toHaveTextContent('coerced');
    expect(countRow).toHaveTextContent('str → 42 (int)');
    expect(screen.getByTestId('pyd-row-handle')).toHaveTextContent('grace-hopper');
  });

  it('renders the typed specimen dump when the whole model validates', async () => {
    stubUseCase(() => success(reportFixture));

    render(<PydLabDemo />);
    fireEvent.click(screen.getByTestId('pyd-fire'));

    await waitFor(() => expect(screen.getByTestId('pyd-specimen')).toBeInTheDocument());
    expect(screen.getByTestId('pyd-specimen')).toHaveTextContent('specimen validates');
    expect(screen.getByTestId('pyd-specimen-dump')).toHaveTextContent('"handle": "grace-hopper"');
  });

  it('renders rejected rows and normalized specimen errors on a constraint violation', async () => {
    stubUseCase(() => success(rejectedFixture));

    render(<PydLabDemo />);
    fireEvent.click(screen.getByTestId('pyd-fire'));

    await waitFor(() => expect(screen.getByTestId('pyd-specimen')).toBeInTheDocument());
    expect(screen.getByTestId('pyd-row-score')).toHaveTextContent('rejected');
    expect(screen.getByTestId('pyd-row-score')).toHaveTextContent('greater_than_equal');
    expect(screen.getByTestId('pyd-specimen')).toHaveTextContent('specimen rejected');
    const errors = screen.getByTestId('pyd-specimen-errors');
    expect(errors).toHaveTextContent('[score]');
    expect(errors).toHaveTextContent('greater than or equal to 1');
  });

  it('switches experiments into the editor', () => {
    stubUseCase(() => success(reportFixture));

    render(<PydLabDemo />);

    fireEvent.click(screen.getByTestId('pyd-preset-bounds'));
    const editor = screen.getByTestId('pyd-payload') as HTMLTextAreaElement;
    expect(editor.value).toContain('"score": 0');

    fireEvent.click(screen.getByTestId('pyd-preset-shape'));
    expect(editor.value).toContain('"tags": "oops"');
  });

  it('refuses invalid editor JSON client-side without firing', () => {
    const fired = stubUseCase(() => success(reportFixture));

    render(<PydLabDemo />);

    fireEvent.change(screen.getByTestId('pyd-payload'), { target: { value: '{oops' } });
    fireEvent.click(screen.getByTestId('pyd-fire'));

    expect(screen.getByTestId('pyd-parse-warning')).toBeInTheDocument();
    expect(fired).toEqual([]);
  });

  it('renders the 422 envelope a refused body earns through the error panel, with recovery', async () => {
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
        : success(reportFixture);
    });

    render(<PydLabDemo />);
    fireEvent.click(screen.getByTestId('pyd-preset-shape'));
    fireEvent.click(screen.getByTestId('pyd-fire'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('validation_failed');

    // Retry re-fires the same payload and the report renders.
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('pyd-table')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });

  it('degrades quietly when the schema cannot be fetched', async () => {
    stubUseCase(() => success(reportFixture), failed(new ServerFailure('down', { code: 'service_unavailable', status: 503, requestId: 'r' })));

    render(<PydLabDemo />);

    await waitFor(() =>
      expect(screen.getByTestId('pyd-schema-unavailable')).toBeInTheDocument(),
    );
  });
});
