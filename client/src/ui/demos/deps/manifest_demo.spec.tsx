import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import DepsManifestDemo from './manifest_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDepsManifestDemoUseCase } from '../../../domain/demo/get-dep-manifest-demo-usecase';
import type { DepsManifestPanel } from '../../../domain/demo/dep-manifest';

/**
 * DepsManifestDemo spec — fixture-driven (happy + failure + degraded): the
 * component resolves its use case through the container, so the spec swaps
 * the token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the panel
 * renders the real-parse rows with each pin beside its range and an honest
 * verdict (satisfied / not judged), the fastapi-rooted tree slice, the
 * agreement cross-check and the lock counts; a degraded available:false
 * payload renders the honest unavailable card; and a failed round degrades
 * to the shared error panel with recovery.
 */

const fakePanel: DepsManifestPanel = {
  manifestFile: 'server/pyproject.toml',
  lockFile: 'server/uv.lock',
  available: true,
  unavailableReason: null,
  requiresPython: '>=3.13',
  groups: [
    {
      group: 'main',
      title: 'Runtime dependencies',
      declaredIn: 'pyproject.toml [project] dependencies',
      directCount: 19,
      note: 'Ships to prod.',
    },
    {
      group: 'dev',
      title: 'Dev group',
      declaredIn: 'pyproject.toml [dependency-groups] dev',
      directCount: 7,
      note: 'Tooling that never ships.',
    },
  ],
  direct: [
    {
      name: 'fastapi',
      group: 'main',
      constraint: '>=0.115',
      lockedVersion: '0.143.1',
      satisfies: true,
      extras: '',
    },
    {
      name: 'sqlalchemy',
      group: 'main',
      constraint: '>=2.1.4',
      lockedVersion: '2.1.4',
      satisfies: true,
      extras: 'asyncio',
    },
    {
      name: 'weirdpkg',
      group: 'main',
      constraint: '>=1,<2',
      lockedVersion: '1.4.0',
      satisfies: null,
      extras: '',
    },
    {
      name: 'grpcio-tools',
      group: 'dev',
      constraint: '>=1.84.0',
      lockedVersion: '1.84.0',
      satisfies: true,
      extras: '',
    },
  ],
  slice: {
    root: 'fastapi',
    rootConstraint: '>=0.115',
    rootLockedVersion: '0.143.1',
    children: [
      { name: 'pydantic', lockedVersion: '2.14.1' },
      { name: 'starlette', lockedVersion: '1.8.0' },
    ],
    note: 'Packages nobody wrote down in the manifest.',
  },
  counts: {
    totalLocked: 76,
    direct: 26,
    transitive: 49,
    note: 'The rest arrived as edges of somebody else\u2019s graph.',
  },
  agreement: {
    manifestNames: 19,
    lockNames: 19,
    missingFromLock: [],
    extraInLock: [],
    agree: true,
  },
  honestyNote: 'Every row is parsed at request time from the two real files.',
};

const degradedPanel: DepsManifestPanel = {
  ...fakePanel,
  available: false,
  unavailableReason: 'FileNotFoundError: no pyproject here',
  requiresPython: null,
  groups: [],
  direct: [],
  slice: null,
  counts: null,
  agreement: null,
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<DepsManifestPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDepsManifestDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetDepsManifestDemoUseCase);
}

describe('DepsManifestDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['deps:manifest']).toBeDefined();
  });

  it('renders the parsed rows: pins beside ranges, honest verdicts, extras, tree, counts', async () => {
    stubUseCase(() => success(fakePanel));

    render(<DepsManifestDemo />);

    await waitFor(() => expect(screen.getByTestId('dm-panel')).toBeInTheDocument());
    expect(screen.getByTestId('dm-files')).toHaveTextContent(
      'server/pyproject.toml + server/uv.lock',
    );
    expect(screen.getByTestId('dm-python')).toHaveTextContent('requires-python >=3.13');
    expect(screen.getByTestId('dm-group-main')).toHaveTextContent('main — 19 direct');
    expect(screen.getByTestId('dm-group-dev')).toHaveTextContent('dev — 7 direct');
    expect(screen.getByTestId('dm-row-fastapi')).toHaveTextContent('>=0.115');
    expect(screen.getByTestId('dm-row-fastapi')).toHaveTextContent('0.143.1');
    expect(screen.getByTestId('dm-verdict-fastapi')).toHaveTextContent('satisfied');
    expect(screen.getByTestId('dm-verdict-weirdpkg')).toHaveTextContent('not judged');
    expect(screen.getByTestId('dm-row-sqlalchemy')).toHaveTextContent('[asyncio]');
    expect(screen.getByTestId('dm-dev-names')).toHaveTextContent('grpcio-tools');
    expect(screen.getByTestId('dm-agreement')).toHaveTextContent('agree');
    expect(screen.getByTestId('dm-slice')).toHaveTextContent('fastapi');
    expect(screen.getByTestId('dm-slice')).toHaveTextContent('starlette 1.8.0');
    expect(screen.getByTestId('dm-counts')).toHaveTextContent('76 total');
    expect(screen.getByTestId('dm-counts')).toHaveTextContent('49 transitive');
    expect(screen.getByTestId('dm-honesty-note')).toHaveTextContent('parsed at request time');
  });

  it('renders the honest unavailable card when the server degraded', async () => {
    stubUseCase(() => success(degradedPanel));

    render(<DepsManifestDemo />);

    await waitFor(() => expect(screen.getByTestId('dm-unavailable')).toBeInTheDocument());
    expect(screen.getByTestId('dm-unavailable')).toHaveTextContent('FileNotFoundError');
    expect(screen.queryByTestId('dm-panel')).not.toBeInTheDocument();
  });

  it('degrades a failed round to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The panel did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-deps-1',
            }),
          )
        : success(fakePanel);
    });

    render(<DepsManifestDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('dm-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
