import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RequestMethodsDemo } from './methods_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { ReqresMethodsDemoUseCase } from '../../../domain/demo/reqres-methods-demo-usecase';
import type {
  MethodsExchange,
  NoteDraft,
  NotesListing,
} from '../../../domain/demo/reqres-methods';

/**
 * RequestMethodsDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration instead of stubbing fetch. Behavior, not implementation: the
 * collection loads on mount (filtered — no revision field), POST reports the
 * 201 exchange with its Location, the invalid-body button surfaces the 422
 * envelope through the shared error panel, and the wire exchange line
 * narrates the last status.
 */

const listingFixture: NotesListing = {
  count: 2,
  notes: [
    {
      id: 1,
      title: 'Read the request first',
      body: 'line, query, headers.',
      tags: ['request'],
      createdAt: '2026-10-15T10:00:00.000+00:00',
    },
    {
      id: 2,
      title: 'Let pydantic own the body',
      body: 'validation before code.',
      tags: ['pydantic'],
      createdAt: '2026-10-15T10:00:01.000+00:00',
    },
  ],
  reasoning: 'GET answered 200 with all 2 notes filtered through NotePublic.',
};

const listExchange: MethodsExchange = {
  method: 'GET',
  path: '/demo/reqres/notes',
  status: 200,
  listing: listingFixture,
};

const createdExchange: MethodsExchange = {
  method: 'POST',
  path: '/demo/reqres/notes',
  status: 201,
  location: '/api/demo/reqres/notes/3',
  note: {
    id: 3,
    title: 'created by spec',
    body: 'b',
    tags: ['t'],
    createdAt: '2026-10-15T10:00:02.000+00:00',
  },
};

/** A fake use case that records drafts and answers scripted Results. */
function stubUseCase(
  respond: (op: string, arg: { id?: number; draft?: NoteDraft }) => Result<MethodsExchange>,
): { drafts: NoteDraft[]; ids: number[] } {
  const drafts: NoteDraft[] = [];
  const ids: number[] = [];
  container.initialize(createAppConfig());
  container.register(ContainerTokens.ReqresMethodsDemoUseCase, {
    list: () => Promise.resolve(respond('list', {})),
    create: (draft: NoteDraft) => {
      drafts.push(draft);
      return Promise.resolve(respond('create', { draft }));
    },
    replace: (id: number, draft: NoteDraft) => {
      ids.push(id);
      drafts.push(draft);
      return Promise.resolve(respond('replace', { id, draft }));
    },
    remove: (id: number) => {
      ids.push(id);
      return Promise.resolve(respond('remove', { id }));
    },
  } as unknown as ReqresMethodsDemoUseCase);
  return { drafts, ids };
}

describe('RequestMethodsDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['reqres:methods']).toBeDefined();
  });

  it('loads the filtered collection on mount and renders the exchange line', async () => {
    stubUseCase((op) => (op === 'list' ? success(listExchange) : success(createdExchange)));

    render(<RequestMethodsDemo />);

    await waitFor(() => expect(screen.getByTestId('rm-listing')).toBeInTheDocument());
    expect(screen.getByTestId('rm-note-1')).toHaveTextContent('Read the request first');
    expect(screen.getByTestId('rm-note-2')).toHaveTextContent('Let pydantic own the body');
    expect(screen.getByTestId('rm-listing')).toHaveTextContent('revision');
    expect(screen.getByTestId('rm-exchange')).toHaveTextContent('GET');
    expect(screen.getByTestId('rm-exchange')).toHaveTextContent('200');
  });

  it('creates from the form and reports the 201 with its Location', async () => {
    const { drafts } = stubUseCase((op) =>
      op === 'list' ? success(listExchange) : success(createdExchange),
    );

    render(<RequestMethodsDemo />);
    await waitFor(() => expect(screen.getByTestId('rm-listing')).toBeInTheDocument());

    fireEvent.change(screen.getByTestId('rm-title'), { target: { value: 'created by spec' } });
    fireEvent.change(screen.getByTestId('rm-body'), { target: { value: 'b' } });
    fireEvent.change(screen.getByTestId('rm-tags'), { target: { value: 't, u' } });
    fireEvent.click(screen.getByTestId('rm-create'));

    await waitFor(() => expect(screen.getByTestId('rm-note')).toBeInTheDocument());
    expect(drafts).toEqual([{ title: 'created by spec', body: 'b', tags: ['t', 'u'] }]);
    expect(screen.getByTestId('rm-exchange')).toHaveTextContent('POST');
    expect(screen.getByTestId('rm-exchange')).toHaveTextContent('201');
    expect(screen.getByTestId('rm-exchange')).toHaveTextContent(
      'location: /api/demo/reqres/notes/3',
    );
    expect(screen.getByTestId('rm-note')).toHaveTextContent('created by spec');
  });

  it('keeps POST disabled until the title is non-empty (server 422 caught earlier)', async () => {
    stubUseCase((op) => (op === 'list' ? success(listExchange) : success(createdExchange)));

    render(<RequestMethodsDemo />);
    await waitFor(() => expect(screen.getByTestId('rm-listing')).toBeInTheDocument());

    expect(screen.getByTestId('rm-create')).toBeDisabled();
    fireEvent.change(screen.getByTestId('rm-title'), { target: { value: 'now valid' } });
    expect(screen.getByTestId('rm-create')).toBeEnabled();
  });

  it('surfaces the 422 envelope via the error panel on the invalid-body button', async () => {
    const { drafts } = stubUseCase((op) =>
      op === 'list'
        ? success(listExchange)
        : failed(
            new ServerFailure('Request validation failed.', {
              code: 'validation_failed',
              status: 422,
              requestId: 'req-77',
            }),
          ),
    );

    render(<RequestMethodsDemo />);
    await waitFor(() => expect(screen.getByTestId('rm-listing')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('rm-invalid'));

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('validation_failed');
    expect(drafts).toEqual([{ title: '', body: '', tags: [] }]);
  });

  it('replaces and deletes the selected note with its id on the wire', async () => {
    const { ids } = stubUseCase((op) => {
      if (op === 'list') return success(listExchange);
      if (op === 'remove') {
        return success({ method: 'DELETE', path: '/demo/reqres/notes/2', status: 204 });
      }
      return success({
        method: 'PUT',
        path: '/demo/reqres/notes/2',
        status: 200,
        note: { ...listingFixture.notes[1]!, title: 'replaced' },
      });
    });

    render(<RequestMethodsDemo />);
    await waitFor(() => expect(screen.getByTestId('rm-listing')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('rm-note-2'));
    expect(screen.getByTestId('rm-replace')).toBeEnabled();
    expect(screen.getByTestId('rm-delete')).toBeEnabled();

    fireEvent.change(screen.getByTestId('rm-title'), { target: { value: 'replaced' } });
    fireEvent.click(screen.getByTestId('rm-replace'));
    await waitFor(() =>
      expect(screen.getByTestId('rm-exchange')).toHaveTextContent('PUT /demo/reqres/notes/2 200'),
    );

    fireEvent.click(screen.getByTestId('rm-delete'));
    await waitFor(() =>
      expect(screen.getByTestId('rm-exchange')).toHaveTextContent(
        'DELETE /demo/reqres/notes/2 204',
      ),
    );
    expect(screen.getByTestId('rm-exchange')).toHaveTextContent('no content');
    expect(ids).toEqual([2, 2]);
  });
});
