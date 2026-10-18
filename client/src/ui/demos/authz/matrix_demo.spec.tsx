import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MatrixDemo } from './matrix_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetAuthzMatrixDemoUseCase } from '../../../domain/demo/get-authz-matrix-demo-usecase';
import type { GetAuthJwtDemoUseCase } from '../../../domain/demo/get-auth-jwt-demo-usecase';
import type {
  AuthzCheckOutcome,
  AuthzPanel,
  EditedPostOutcome,
} from '../../../domain/demo/authz-matrix';

/**
 * MatrixDemo spec — fixture-driven (happy + failure): the panel renders the
 * principals with roles, the roles→grants matrix, and the targets; the check
 * runs the engine (allow and deny with reasons); "try it for real" mints a
 * token through the jwt lab's use case and shows the guarded endpoint's 200
 * reason — or the 403 envelope's message when the wire verdict denies; a
 * failed panel degrades to the shared error panel with recovery.
 */

const panel: AuthzPanel = {
  principals: [
    {
      name: 'grace',
      displayName: 'Grace Hopper',
      role: 'author',
      kind: 'user',
      note: 'owns four posts; can edit HER posts only',
    },
  ],
  roles: [
    {
      role: 'author',
      grants: [
        { action: 'posts:read', level: 'any' },
        { action: 'posts:write', level: 'own' },
        { action: 'comments:read', level: 'any' },
        { action: 'comments:moderate', level: null },
      ],
    },
  ],
  seededPosts: [
    { id: 'designing-urls-people-can-read', title: 'Designing URLs people can read', author: 'grace' },
    { id: 'idempotency-retold', title: 'Idempotency, retold', author: 'alan' },
  ],
  seededComments: [
    { id: 'urls-are-for-machines', postId: 'designing-urls-people-can-read', author: 'alan', status: 'visible' },
  ],
  wildcardScope: '*',
  denyNote: 'deny by default',
  scopeNote: 'scopes narrow, never widen',
  ownershipNote: 'own-reach answers can edit THIS one',
  checkEndpoint: '/api/demo/authz/check',
  editPostEndpoint: '/api/demo/authz/posts/{post_id}',
  moderateCommentEndpoint: '/api/demo/authz/comments/{comment_id}/moderate',
  reasoning: 'Four roles over four actions, two reaches.',
};

const allowCheck: AuthzCheckOutcome = {
  principal: 'grace',
  role: 'author',
  scopes: ['*'],
  action: 'posts:write',
  resource: { kind: 'post', id: 'designing-urls-people-can-read', owner: 'grace' },
  decision: {
    allowed: true,
    reason: "posts:write is own-scoped for role 'author' and 'grace' owns this post",
  },
  detail: "'grace' (author, scopes [*]) asks for 'posts:write' — the engine says ALLOW",
};

const denyCheck: AuthzCheckOutcome = {
  ...allowCheck,
  resource: { kind: 'post', id: 'idempotency-retold', owner: 'alan' },
  decision: {
    allowed: false,
    reason: "posts:write is own-scoped, and this post 'idempotency-retold' belongs to 'alan', not 'grace'",
  },
};

const edited: EditedPostOutcome = {
  principal: 'grace',
  principalKind: 'user',
  action: 'posts:write',
  resourceKind: 'post',
  resourceId: 'designing-urls-people-can-read',
  reason: 'ownership is the authority here',
  via: 'Authorization: Bearer',
  detail: 'the guard ran before the handler',
  post: {
    id: 'designing-urls-people-can-read',
    title: 'Designing URLs people can read',
    author: 'grace',
    body: 'A URL is part of the interface.',
    tags: ['design', 'http'],
    status: 'published',
  },
};

type Stubs = {
  panel?: () => Promise<Result<AuthzPanel>>;
  check?: (principal: string, action: string) => Promise<Result<AuthzCheckOutcome>>;
  editPost?: () => Promise<Result<EditedPostOutcome>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetAuthzMatrixDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    check:
      stubs.check ??
      (async (_principal: string, action: string) =>
        success(action === 'posts:write' ? allowCheck : denyCheck)),
    editPost: stubs.editPost ?? (async () => success(edited)),
  } as unknown as GetAuthzMatrixDemoUseCase);
  container.register(ContainerTokens.GetAuthJwtDemoUseCase, {
    mint: async () =>
      success({
        accessToken: 'token',
        tokenType: 'bearer',
        expiresIn: 900,
        header: { alg: 'HS256', typ: 'JWT' },
        payload: {},
        signedWith: 'real',
        expiresAt: '2026-10-17T00:00:00.000+00:00',
        detail: 'minted',
      }),
  } as unknown as GetAuthJwtDemoUseCase);
}

describe('MatrixDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['authz:matrix']).toBeDefined();
  });

  it('renders the roster, the matrix, and the targets', async () => {
    stubUseCase({});
    render(<MatrixDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-principals')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('authz-matrix-principals')).toHaveTextContent(
      'grace · author',
    );
    expect(screen.getByTestId('authz-matrix-matrix')).toHaveTextContent(
      'posts:write=own',
    );
    expect(screen.getByTestId('authz-matrix-matrix')).toHaveTextContent(
      'comments:moderate=—',
    );
    expect(screen.getByTestId('authz-matrix-targets')).toHaveTextContent(
      'comment urls-are-for-machines · owner alan',
    );
  });

  it('runs the check and shows the engine verdict with its reason', async () => {
    let asked = '';
    stubUseCase({
      check: async (principal, action) => {
        asked = `${principal}:${action}`;
        return success(asked === 'grace:posts:write' ? allowCheck : denyCheck);
      },
    });
    render(<MatrixDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-principals')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'run the check' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-check-result')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('authz-matrix-check-result')).toHaveTextContent('ALLOW');
    expect(asked).toBe('grace:posts:write');
  });

  it('tries it for real: mints a token and shows the 200 with its reason', async () => {
    stubUseCase({});
    render(<MatrixDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-principals')).toBeInTheDocument(),
    );

    const postOption = screen
      .getAllByRole('combobox')
      .find((box) => box.textContent?.includes('designing-urls')) as HTMLSelectElement;
    postOption.value = 'post:designing-urls-people-can-read';
    postOption.dispatchEvent(new Event('change', { bubbles: true }));

    screen.getByRole('button', { name: 'try it for real' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-real-result')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('authz-matrix-real-result')).toHaveTextContent(
      '200 · grace',
    );
    expect(screen.getByTestId('authz-matrix-real-result')).toHaveTextContent(
      'ownership is the authority here',
    );
  });

  it('shows the 403 envelope message when the wire verdict denies', async () => {
    stubUseCase({
      editPost: async () =>
        failed(
          new ServerFailure(
            "forbidden — posts:write denied for 'alan': no role of ('viewer') grants posts:write",
            { code: 'forbidden', status: 403, requestId: 'req-a1' },
          ),
        ),
    });
    render(<MatrixDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-principals')).toBeInTheDocument(),
    );

    const postOption = screen
      .getAllByRole('combobox')
      .find((box) => box.textContent?.includes('designing-urls')) as HTMLSelectElement;
    postOption.value = 'post:designing-urls-people-can-read';
    postOption.dispatchEvent(new Event('change', { bubbles: true }));

    screen.getByRole('button', { name: 'try it for real' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-real-result')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('authz-matrix-real-result')).toHaveTextContent(
      'forbidden: forbidden — posts:write denied',
    );
  });

  it('degrades to the shared error panel on a Failed panel, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      panel: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Could not reach the server.', {
                code: 'unknown_error',
                status: 0,
                requestId: 'req-h1',
              }),
            )
          : success(panel);
      },
    });
    render(<MatrixDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('authz-matrix-principals')).toBeInTheDocument(),
    );
  });
});
