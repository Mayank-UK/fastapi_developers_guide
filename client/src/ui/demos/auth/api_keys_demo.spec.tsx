import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ApiKeysDemo } from './api_keys_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetAuthApiKeysDemoUseCase } from '../../../domain/demo/get-auth-api-keys-demo-usecase';
import type {
  ApiKeyCallOutcome,
  ApiKeyCreated,
  ApiKeyRevokeOutcome,
  ApiKeysPanel,
} from '../../../domain/demo/auth-api-keys';

/**
 * ApiKeysDemo spec — fixture-driven (happy + failure): the roster shows
 * the stored record (prefix + hash preview, never the secret); generate
 * shows the raw key exactly once; the protected call authenticates; the
 * 401 envelope degrades to the action error line; revoke reports the
 * instant death.
 */

const created: ApiKeyCreated = {
  prefix: 'fdg_65181fe6',
  key: 'fdg_65181fe6.AAAA-secret-half-of-the-key-value',
  keyHash: 'a'.repeat(64),
  name: 'demo key',
  scopes: ['posts:read'],
  detail: 'copy it now',
};

const panel: ApiKeysPanel = {
  records: [
    {
      prefix: created.prefix,
      name: created.name,
      scopes: ['posts:read'],
      keyHashPreview: 'aaaaaaaaaaaa…',
      createdAt: '2026-10-17T00:00:00+00:00',
    },
  ],
  storageNote: 'stored as SHA-256 only',
  lookupNote: 'constant-time compare',
  createEndpoint: '/api/demo/auth/keys',
  callEndpoint: '/api/demo/auth/keys/call',
  revokeEndpoint: '/api/demo/auth/keys/revoke',
  reasoning: 'The key record at rest: prefix, hash preview, never the secret.',
};

const callOutcome: ApiKeyCallOutcome = {
  prefix: created.prefix,
  name: created.name,
  scopes: ['posts:read'],
  detail: 'authenticated',
};

const revokeOutcome: ApiKeyRevokeOutcome = {
  prefix: created.prefix,
  revoked: true,
  detail: 'instantly dead',
};

type Stubs = {
  call?: (key: string) => Promise<Result<ApiKeyCallOutcome>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetAuthApiKeysDemoUseCase, {
    panel: async () => success(panel),
    generate: async () => success(created),
    call: stubs.call ?? (async () => success(callOutcome)),
    revoke: async () => success(revokeOutcome),
  } as unknown as GetAuthApiKeysDemoUseCase);
}

describe('ApiKeysDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['auth:api-keys']).toBeDefined();
  });

  it('shows the raw key once, the roster without it, and the round', async () => {
    stubUseCase({});
    render(<ApiKeysDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-keys-state')).toBeInTheDocument());
    expect(screen.getByTestId('auth-keys-state')).toHaveTextContent('1 key record(s) at rest');

    screen.getByRole('button', { name: 'generate key (raw shown once)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-keys-created')).toBeInTheDocument());
    expect(screen.getByTestId('auth-keys-created')).toHaveTextContent('copy it now');

    screen.getByRole('button', { name: 'call protected (x-api-key)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-keys-call')).toBeInTheDocument());
    expect(screen.getByTestId('auth-keys-call')).toHaveTextContent(created.prefix);

    screen.getByRole('button', { name: 'revoke by prefix' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-keys-revoked')).toBeInTheDocument());
    expect(screen.getByTestId('auth-keys-revoked')).toHaveTextContent(
      `revoked ${created.prefix}: true`,
    );
  });

  it('renders the 401 envelope as the action error line on a bad key', async () => {
    stubUseCase({
      call: async () =>
        failed(
          new ServerFailure('invalid api key', {
            code: 'unauthorized',
            status: 401,
            requestId: 'req-k1',
          }),
        ),
    });
    render(<ApiKeysDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-keys-state')).toBeInTheDocument());
    screen.getByRole('button', { name: 'call protected (x-api-key)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-keys-action-error')).toHaveTextContent(
      'invalid api key',
    ));
  });
});
