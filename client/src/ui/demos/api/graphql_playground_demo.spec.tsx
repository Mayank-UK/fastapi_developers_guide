import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GraphqlPlaygroundDemo } from './graphql_playground_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetGraphqlPlaygroundDemoUseCase } from '../../../domain/demo/get-graphql-playground-demo-usecase';
import type {
  GraphqlExample,
  GraphqlPlayground,
  GraphqlRunResult,
} from '../../../domain/demo/graphql-playground';

/**
 * GraphqlPlaygroundDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration (the container's documented
 * replace-a-singleton seam) instead of stubbing fetch. Behavior, not
 * implementation: the package renders the endpoint and the tour, an
 * example click loads its operation into the editor (an empty editor
 * refuses to fire), Run POSTs the trimmed editor text through the use
 * case and renders BOTH honest GraphQL outcomes (data, and errors with
 * the family code), and failures degrade to the shared error panel with
 * recovery.
 */

const pageExample: GraphqlExample = {
  id: 'page',
  label: 'A page of posts',
  description: 'The collection read.',
  query: 'query { posts(limit: 3) { total } }',
};

const errorExample: GraphqlExample = {
  id: 'error',
  label: 'A not-found error',
  description: 'An unknown slug answers 200 with errors.',
  query: 'query { post(slug: "no-such-post") { id } }',
};

const fixture: GraphqlPlayground = {
  endpoint: '/api/graphql',
  sdl: 'type Query {\n  posts: PostPage\n}',
  examples: [pageExample, errorExample],
  reasoning: 'The SDL below is the running schema exactly as strawberry serves it.',
};

const dataResult: GraphqlRunResult = {
  data: { posts: { total: 12 } },
};

const errorsResult: GraphqlRunResult = {
  errors: [
    {
      message: "Post 'no-such-post' not found",
      locations: [{ line: 1, column: 3 }],
      path: ['post'],
      extensions: { code: 'not_found', slug: 'no-such-post' },
    },
  ],
};

type StubUseCase = {
  playground: () => Promise<Result<GraphqlPlayground>>;
  run: (query: string) => Promise<Result<GraphqlRunResult>>;
};

function stubUseCase(overrides: Partial<StubUseCase>): void {
  container.initialize(createAppConfig());
  const useCase = {
    playground: async () => success(fixture),
    run: async () => success(dataResult),
    ...overrides,
  };
  container.register(
    ContainerTokens.GetGraphqlPlaygroundDemoUseCase,
    useCase as unknown as GetGraphqlPlaygroundDemoUseCase,
  );
}

describe('GraphqlPlaygroundDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['api:graphql-playground']).toBeDefined();
  });

  it('renders loading first, then the package: endpoint, tour, editor, SDL', async () => {
    stubUseCase({});

    render(<GraphqlPlaygroundDemo />);

    expect(screen.getByTestId('gp-loading')).toBeInTheDocument();

    await waitFor(() => expect(screen.getByTestId('gp-package')).toBeInTheDocument());
    expect(screen.getByTestId('gp-endpoint')).toHaveTextContent('/api/graphql');
    expect(screen.getAllByTestId('gp-example')).toHaveLength(2);

    // The editor starts empty: the note says so and Run stays disabled.
    expect(screen.getByTestId('gp-editor')).toHaveValue('');
    expect(screen.getByTestId('gp-empty-note')).toBeInTheDocument();
    expect(screen.getByTestId('gp-run')).toBeDisabled();

    expect(screen.getByTestId('gp-sdl')).toHaveTextContent('type Query');
    expect(screen.getByTestId('gp-reasoning')).toHaveTextContent('running schema');
  });

  it('loads an example into the editor and fires it through the use case', async () => {
    const fired: string[] = [];
    stubUseCase({ run: async (query) => (fired.push(query), success(dataResult)) });

    render(<GraphqlPlaygroundDemo />);
    await waitFor(() => expect(screen.getByTestId('gp-package')).toBeInTheDocument());

    fireEvent.click(screen.getByText(pageExample.label));

    const editor = screen.getByTestId('gp-editor');
    expect(editor).toHaveValue(pageExample.query);
    expect(screen.queryByTestId('gp-empty-note')).not.toBeInTheDocument();
    expect(screen.getByTestId('gp-run')).toBeEnabled();

    fireEvent.click(screen.getByTestId('gp-run'));

    await waitFor(() => expect(screen.getByTestId('gp-result')).toBeInTheDocument());
    expect(fired).toEqual([pageExample.query]);
    expect(screen.getByTestId('gp-result-data')).toHaveTextContent('"total": 12');
  });

  it('renders a 200-with-errors answer as the protocol failure shape, inline', async () => {
    stubUseCase({ run: async () => success(errorsResult) });

    render(<GraphqlPlaygroundDemo />);
    await waitFor(() => expect(screen.getByTestId('gp-package')).toBeInTheDocument());

    fireEvent.click(screen.getByText(errorExample.label));
    fireEvent.click(screen.getByTestId('gp-run'));

    await waitFor(() => expect(screen.getByTestId('gp-result-errors')).toBeInTheDocument());
    const panel = screen.getByTestId('gp-result-errors');
    expect(panel).toHaveTextContent("Post 'no-such-post' not found");
    expect(panel).toHaveTextContent('at 1:3');
    expect(panel).toHaveTextContent('path: post');
    expect(panel).toHaveTextContent('code: not_found');
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      playground: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('The GraphQL endpoint is down.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-13',
              }),
            )
          : success(fixture);
      },
    });

    render(<GraphqlPlaygroundDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(screen.getByTestId('gp-package')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
