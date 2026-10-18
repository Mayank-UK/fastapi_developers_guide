import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { HashingDemo } from './hashing_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetAuthHashingDemoUseCase } from '../../../domain/demo/get-auth-hashing-demo-usecase';
import type {
  HashingPanel,
  PasswordHashOutcome,
  PasswordVerifyOutcome,
} from '../../../domain/demo/auth-hashing';

/**
 * HashingDemo spec — fixture-driven (happy + failure): the panel renders
 * the active + legacy cost and the seeded previews; hash shows the honest
 * milliseconds; verify shows ok / needsRehash for the right password, the
 * wrong password, and the legacy hash; a failed roster degrades to the
 * shared error panel with recovery.
 */

const panel: HashingPanel = {
  algorithm: 'argon2id',
  parameters: 'argon2id · m=65536 KiB · t=3 · p=4',
  legacyParameters: 'argon2id · m=8192 KiB · t=1 · p=2 (2015-era cost)',
  seedCredentials: [
    {
      username: 'ada',
      displayName: 'Ada Lovelace',
      hashPreview: '$argon2id$v=19$m=65536,t=3,p=4$kwLr…',
      scopes: ['posts:read', 'posts:write'],
    },
  ],
  distinctionNote: 'hashing is one-way',
  loggingNote: 'log lines carry the outcome, never the secret',
  hashEndpoint: '/api/demo/auth/hashing/hash',
  verifyEndpoint: '/api/demo/auth/hashing/verify',
  reasoning: 'The active cost is argon2id at 64 MiB.',
};

const hashed: PasswordHashOutcome = {
  hash: '$argon2id$v=19$m=65536,t=3,p=4$newsalt$newhash',
  algorithm: 'argon2id',
  parameters: panel.parameters,
  elapsedMs: 31,
  detail: 'argon2 hashed the password in 31 ms',
};

const okVerdict: PasswordVerifyOutcome = {
  ok: true,
  needsRehash: false,
  elapsedMs: 30,
  error: null,
  detail: 'password CORRECT',
};

const legacyVerdict: PasswordVerifyOutcome = {
  ok: true,
  needsRehash: true,
  elapsedMs: 4,
  error: null,
  detail: 'behind the current parameters — rehash on this login',
};

type Stubs = {
  verify?: (password: string, hash: string) => Promise<Result<PasswordVerifyOutcome>>;
  panel?: () => Promise<Result<HashingPanel>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetAuthHashingDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    hash: async () => success(hashed),
    verify: stubs.verify ?? (async () => success(okVerdict)),
  } as unknown as GetAuthHashingDemoUseCase);
}

describe('HashingDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['auth:hashing']).toBeDefined();
  });

  it('renders the contract, the honest cost, and the verify verdicts', async () => {
    stubUseCase({ verify: async (password) => success(password.includes('!') ? { ...okVerdict, ok: false } : password === 'analytical-engine' ? legacyVerdict : okVerdict) });
    render(<HashingDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-hashing-state')).toBeInTheDocument());
    expect(screen.getByTestId('auth-hashing-state')).toHaveTextContent('m=65536');

    screen.getByRole('button', { name: 'hash (fresh salt)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-hashing-hashed')).toBeInTheDocument());
    expect(screen.getByTestId('auth-hashing-hashed')).toHaveTextContent('31 ms');

    screen.getByRole('button', { name: 'verify (right password)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-hashing-verified')).toBeInTheDocument());
    expect(screen.getByTestId('auth-hashing-verified')).toHaveTextContent('ok: true');

    screen.getByRole('button', { name: 'verify (WRONG password)' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('auth-hashing-verified')).toHaveTextContent('ok: false'),
    );

    screen.getByRole('button', { name: 'verify legacy hash (rehash flag)' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('auth-hashing-verified')).toHaveTextContent(
        'needsRehash: true',
      ),
    );
  });

  it('degrades to the shared error panel on a Failed roster, with recovery', async () => {
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
    render(<HashingDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-hashing-state')).toBeInTheDocument());
  });
});
