import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PostsWorkbenchDemo } from './posts_workbench_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetPostsWorkbenchDemoUseCase } from '../../../domain/demo/get-posts-workbench-demo-usecase';
import type {
  WorkbenchOutcome,
  WorkbenchRoster,
  WorkbenchRound,
} from '../../../domain/demo/posts-workbench';

/**
 * PostsWorkbenchDemo spec — fixture-driven (happy + failure): the
 * component resolves its use case through the container, so the spec
 * swaps the token registration (the container's documented
 * replace-a-singleton seam) instead of stubbing fetch. Behavior, not
 * implementation: the facets fetch on mount and feed the filter pickers,
 * a list round fires the assembled query verbatim and renders the page +
 * pagination + layer stack, template/method switches reshape the form,
 * the 404 and 405 outcomes render through the envelope panel, invalid
 * editor JSON is refused client-side, and failures degrade to the shared
 * error panel with recovery.
 */

const rosterFixture: WorkbenchRoster = {
  authors: ['alan', 'barbara', 'grace'],
  tags: ['api', 'design', 'http'],
  statuses: ['draft', 'published'],
  sorts: ['newest', 'oldest', 'title'],
  totalPosts: 12,
  reasoning: 'The workbench runs over the REAL /api/posts substrate: 12 posts live.',
};

const listOutcomeFixture: WorkbenchOutcome = {
  operation: 'list',
  request: { method: 'GET', template: '/api/posts', path: '/api/posts?limit=3&author=grace' },
  status: 200,
  statusReason: '200 OK',
  kind: 'page',
  page: {
    items: [
      {
        id: 'designing-urls-people-can-read',
        title: 'Designing URLs people can read',
        body: 'A URL is part of the interface.',
        author: 'grace',
        tags: ['design', 'http'],
        status: 'published',
        createdAt: '2026-09-01T08:00:00.000+00:00',
        updatedAt: '2026-09-01T08:00:00.000+00:00',
      },
    ],
    total: 4,
    page: 1,
    limit: 3,
    pages: 2,
  },
  pagination: {
    total: 4,
    page: 1,
    limit: 3,
    pages: 2,
    next: '/api/posts?limit=3&author=grace&page=2',
  },
  layers: [
    { name: 'routing', detail: 'GET /api/posts matched the collection route' },
    { name: 'validation', detail: 'query bound through PostListQuery' },
    { name: 'use case', detail: 'ListPostsUseCase.execute ran' },
    { name: 'repository', detail: 'filtered author=grace, sliced page 1 of 2' },
    { name: 'response', detail: 'PostPage serialized; headers stamped' },
  ],
  reasoning: 'The real GET /api/posts answers 200 with this page.',
};

const envelopeOutcomeFixture: WorkbenchOutcome = {
  operation: 'get',
  request: {
    method: 'GET',
    template: '/api/posts/{postId}',
    path: '/api/posts/nope',
  },
  status: 404,
  statusReason: '404 Not Found',
  kind: 'envelope',
  envelope: { code: 'not_found', message: "Post 'nope' not found", requestId: 'req-404' },
  layers: [
    { name: 'routing', detail: 'matched the item route' },
    { name: 'validation', detail: 'path parameter is a str' },
    { name: 'use case', detail: 'GetPostUseCase returned Err(not_found)' },
    { name: 'response', detail: 'the shared handler rendered the envelope' },
  ],
  reasoning: 'The real GET would answer 404 with this exact envelope.',
};

const methodNotAllowedFixture: WorkbenchOutcome = {
  operation: 'method-not-allowed',
  request: { method: 'DELETE', template: '/api/posts', path: '/api/posts' },
  status: 405,
  statusReason: '405 Method Not Allowed',
  kind: 'envelope',
  envelope: { code: 'not_found', message: 'Method Not Allowed', requestId: 'req-405' },
  layers: [
    { name: 'routing', detail: 'DELETE + /api/posts matches no route' },
    { name: 'response', detail: 'Starlette answers 405; the handler wraps it' },
  ],
  reasoning: 'No route answers DELETE /api/posts, so the framework replies 405.',
};

const createOutcomeFixture: WorkbenchOutcome = {
  operation: 'create',
  request: {
    method: 'POST',
    template: '/api/posts',
    path: '/api/posts',
    body: { title: 'A post from the workbench', author: 'grace', tags: ['api'], status: 'published' },
  },
  status: 201,
  statusReason: '201 Created',
  kind: 'post',
  post: {
    id: 'a-post-from-the-workbench',
    title: 'A post from the workbench',
    body: '',
    author: 'grace',
    tags: ['api'],
    status: 'published',
    createdAt: '2026-10-15T00:00:00.000+00:00',
    updatedAt: '2026-10-15T00:00:00.000+00:00',
  },
  layers: [
    { name: 'routing', detail: 'POST /api/posts matched the collection route' },
    { name: 'validation', detail: 'body validated through PostCreate' },
    { name: 'use case', detail: 'CreatePostUseCase.execute handed the draft to the port' },
    { name: 'repository', detail: 'minted the slug, stored the snapshot' },
    { name: 'response', detail: '201 Created; Location names the new resource' },
  ],
  reasoning: 'The repository genuinely holds it now.',
};

/** Capture the rounds the component fired, answering with a fixture. */
function stubUseCase(
  respond: (round: WorkbenchRound) => Result<WorkbenchOutcome>,
  roster: Result<WorkbenchRoster> = success(rosterFixture),
): WorkbenchRound[] {
  const fired: WorkbenchRound[] = [];
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetPostsWorkbenchDemoUseCase, {
    roster: () => Promise.resolve(roster),
    run: (round: WorkbenchRound) => {
      fired.push(round);
      return Promise.resolve(respond(round));
    },
  } as unknown as GetPostsWorkbenchDemoUseCase);
  return fired;
}

describe('PostsWorkbenchDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['api:posts-workbench']).toBeDefined();
  });

  it('fetches the facets on mount and renders the filter pickers from them', async () => {
    stubUseCase(() => success(listOutcomeFixture));

    render(<PostsWorkbenchDemo />);

    await waitFor(() => expect(screen.getByTestId('pw-form')).toBeInTheDocument());
    const author = screen.getByTestId('pw-author') as HTMLSelectElement;
    expect([...author.options].map((option) => option.value)).toEqual([
      '',
      'alan',
      'barbara',
      'grace',
    ]);
    expect(screen.getByTestId('pw-idle')).toHaveTextContent('REAL /api/posts substrate');
    expect(screen.getByTestId('pw-query')).toBeInTheDocument();
  });

  it('fires the assembled list query verbatim and renders page, pagination, and layers', async () => {
    const fired = stubUseCase(() => success(listOutcomeFixture));

    render(<PostsWorkbenchDemo />);
    await waitFor(() => expect(screen.getByTestId('pw-form')).toBeInTheDocument());

    fireEvent.change(screen.getByTestId('pw-limit'), { target: { value: '3' } });
    fireEvent.change(screen.getByTestId('pw-author'), { target: { value: 'grace' } });
    fireEvent.click(screen.getByTestId('pw-fire'));

    await waitFor(() => expect(screen.getByTestId('pw-outcome')).toBeInTheDocument());
    expect(fired).toEqual([
      { method: 'GET', template: '/api/posts', query: { page: 1, limit: 3, sort: 'newest', author: 'grace' } },
    ]);
    expect(screen.getByTestId('pw-status')).toHaveTextContent('200 OK');
    expect(screen.getByTestId('pw-request')).toHaveTextContent('GET /api/posts?limit=3&author=grace');
    expect(screen.getByTestId('pw-page-payload')).toHaveTextContent(
      'designing-urls-people-can-read',
    );
    expect(screen.getByTestId('pw-pagination')).toHaveTextContent('page 1 of 2');
    expect(screen.getByTestId('pw-pagination')).toHaveTextContent('next: /api/posts?limit=3&author=grace&page=2');
    expect(screen.getByTestId('pw-layers')).toHaveTextContent('repository');
  });

  it('switching to the item template reshapes the form and fires the postId', async () => {
    const fired = stubUseCase(() => success(envelopeOutcomeFixture));

    render(<PostsWorkbenchDemo />);
    await waitFor(() => expect(screen.getByTestId('pw-form')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('pw-template-item'));
    fireEvent.change(screen.getByTestId('pw-post-id'), { target: { value: 'nope' } });
    fireEvent.click(screen.getByTestId('pw-fire'));

    await waitFor(() => expect(screen.getByTestId('pw-outcome')).toBeInTheDocument());
    expect(fired).toEqual([
      { method: 'GET', template: '/api/posts/{postId}', postId: 'nope' },
    ]);
    expect(screen.queryByTestId('pw-query')).not.toBeInTheDocument();
    expect(screen.getByTestId('pw-envelope')).toHaveTextContent('not_found');
    expect(screen.getByTestId('pw-envelope')).toHaveTextContent("Post 'nope' not found");
    expect(screen.getByTestId('pw-status')).toHaveTextContent('404 Not Found');
  });

  it('DELETE fires without a body and renders the honest 405 envelope', async () => {
    const fired = stubUseCase(() => success(methodNotAllowedFixture));

    render(<PostsWorkbenchDemo />);
    await waitFor(() => expect(screen.getByTestId('pw-form')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('pw-method-DELETE'));
    fireEvent.click(screen.getByTestId('pw-fire'));

    await waitFor(() => expect(screen.getByTestId('pw-outcome')).toBeInTheDocument());
    expect(fired).toEqual([{ method: 'DELETE', template: '/api/posts' }]);
    expect(screen.getByTestId('pw-status')).toHaveTextContent('405 Method Not Allowed');
    expect(screen.getByTestId('pw-envelope')).toHaveTextContent('Method Not Allowed');
    expect(screen.getByTestId('pw-layers')).toHaveTextContent('matches no route');
  });

  it('POST fires the edited body verbatim and renders the created post', async () => {
    const fired = stubUseCase(() => success(createOutcomeFixture));

    render(<PostsWorkbenchDemo />);
    await waitFor(() => expect(screen.getByTestId('pw-form')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('pw-method-POST'));
    fireEvent.click(screen.getByTestId('pw-fire'));

    await waitFor(() => expect(screen.getByTestId('pw-outcome')).toBeInTheDocument());
    expect(fired).toHaveLength(1);
    expect(fired[0]?.method).toBe('POST');
    expect(fired[0]?.body).toEqual({
      title: 'A post from the workbench',
      author: 'grace',
      tags: ['api'],
      status: 'published',
    });
    expect(screen.getByTestId('pw-post')).toHaveTextContent('a-post-from-the-workbench');
    expect(screen.getByTestId('pw-status')).toHaveTextContent('201 Created');
  });

  it('refuses invalid body JSON client-side without firing', async () => {
    const fired = stubUseCase(() => success(createOutcomeFixture));

    render(<PostsWorkbenchDemo />);
    await waitFor(() => expect(screen.getByTestId('pw-form')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('pw-method-POST'));
    fireEvent.change(screen.getByTestId('pw-body'), { target: { value: '{oops' } });
    fireEvent.click(screen.getByTestId('pw-fire'));

    expect(screen.getByTestId('pw-parse-warning')).toBeInTheDocument();
    expect(fired).toEqual([]);
  });

  it('renders a failed round through the error panel, with recovery', async () => {
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
        : success(listOutcomeFixture);
    });

    render(<PostsWorkbenchDemo />);
    await waitFor(() => expect(screen.getByTestId('pw-form')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('pw-method-DELETE'));
    fireEvent.click(screen.getByTestId('pw-fire'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('validation_failed');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('pw-outcome')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });

  it('renders the roster failure through the error panel', async () => {
    stubUseCase(
      () => success(listOutcomeFixture),
      failed(new ServerFailure('down', { code: 'service_unavailable', status: 503, requestId: 'r' })),
    );

    render(<PostsWorkbenchDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');
  });
});
