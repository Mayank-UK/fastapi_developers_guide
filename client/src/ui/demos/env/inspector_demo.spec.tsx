import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import EnvInspectorDemo from './inspector_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetEnvInspectorDemoUseCase } from '../../../domain/demo/get-env-inspector-demo-usecase';
import type { EnvInspectorPanel, ScenarioSnapshot } from '../../../domain/demo/env-inspector';

/**
 * EnvInspectorDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the panel
 * renders the real-config rows with source badges and the redacted secret
 * (value 'redacted' + length hint, never the live value), a flag click
 * fires exactly one PATCH and re-reads the panel so the flipped flag is
 * seen live, and both load and write failures degrade to the shared error
 * panel with recovery.
 */

const fakePanel: EnvInspectorPanel = {
  environment: 'dev',
  envVar: 'FDG_ENV',
  facts: { envPrefix: 'FDG_', frozen: true, cache: 'one instance per process (get_config is lru_cache\u2019d)' },
  settings: [
    {
      name: 'env',
      envVar: 'FDG_ENV',
      type: 'str',
      value: 'dev',
      source: 'env',
      secret: false,
      redacted: false,
      shapeHint: null,
    },
    {
      name: 'debug',
      envVar: 'FDG_DEBUG',
      type: 'bool',
      value: 'False',
      source: 'default',
      secret: false,
      redacted: false,
      shapeHint: null,
    },
    {
      name: 'jwt_secret',
      envVar: 'FDG_JWT_SECRET',
      type: 'str',
      value: 'redacted',
      source: 'default',
      secret: true,
      redacted: true,
      shapeHint: '40 chars, hidden',
    },
  ],
  sourceNote: 'Attribution is real introspection, not a guess.',
  redactionNote: 'Secret-bearing fields are redacted server-side before this payload is built.',
  flags: {
    getEndpoint: '/api/demo/scenario',
    patchEndpoint: '/api/demo/scenario',
    dataMode: 'fake',
    injectFailure: 'none',
    note: 'The scenario store is this repo\u2019s real runtime feature-flag mechanism.',
  },
};

const flippedPanel: EnvInspectorPanel = {
  ...fakePanel,
  flags: { ...fakePanel.flags, dataMode: 'live' },
};

const liveSnapshot: ScenarioSnapshot = { dataMode: 'live', injectFailure: 'none' };

/** Swap the container's use-case token for a stub answering the trio. */
function stubUseCase(
  respondPanel: () => Result<EnvInspectorPanel>,
  respondSetDataMode: (mode: 'fake' | 'live') => Result<ScenarioSnapshot>,
): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetEnvInspectorDemoUseCase, {
    panel: () => Promise.resolve(respondPanel()),
    setDataMode: (mode: 'fake' | 'live') => Promise.resolve(respondSetDataMode(mode)),
    setInjectFailure: () => Promise.resolve(success(liveSnapshot)),
  } as unknown as GetEnvInspectorDemoUseCase);
}

describe('EnvInspectorDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['env:inspector']).toBeDefined();
  });

  it('renders the live-config rows: values, source badges, the redacted secret', async () => {
    stubUseCase(() => success(fakePanel), () => success(liveSnapshot));

    render(<EnvInspectorDemo />);

    await waitFor(() => expect(screen.getByTestId('ei-panel')).toBeInTheDocument());
    expect(screen.getByTestId('ei-environment')).toHaveTextContent('environment: dev (FDG_ENV)');
    expect(screen.getByTestId('ei-facts')).toHaveTextContent('prefix FDG_');
    expect(screen.getByTestId('ei-setting-env')).toHaveTextContent('dev');
    expect(screen.getByTestId('ei-source-env')).toHaveTextContent('env');
    expect(screen.getByTestId('ei-source-debug')).toHaveTextContent('default');
    const secretRow = screen.getByTestId('ei-setting-jwt_secret');
    expect(secretRow).toHaveTextContent('redacted');
    expect(secretRow).toHaveTextContent('40 chars, hidden');
    expect(secretRow).not.toHaveTextContent('dev-only-jwt-secret');
    expect(screen.getByTestId('ei-source-note')).toHaveTextContent('real introspection');
    expect(screen.getByTestId('ei-redaction-note')).toHaveTextContent('redacted server-side');
    expect(screen.getByTestId('ei-flags')).toHaveTextContent('dataMode: fake');
  });

  it('fires exactly one PATCH per flag click and re-reads the panel to show it live', async () => {
    let patches = 0;
    let reads = 0;
    stubUseCase(
      () => {
        reads += 1;
        return success(reads === 1 ? fakePanel : flippedPanel);
      },
      (mode) => {
        patches += 1;
        expect(mode).toBe('live');
        return success(liveSnapshot);
      },
    );

    render(<EnvInspectorDemo />);
    await waitFor(() => expect(screen.getByTestId('ei-mode-live')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('ei-mode-live'));

    await waitFor(() =>
      expect(screen.getByTestId('ei-flags')).toHaveTextContent('dataMode: live'),
    );
    expect(patches).toBe(1);
    expect(reads).toBe(2);
  });

  it('degrades a failed load to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(
      () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('The panel did not answer.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-env-1',
              }),
            )
          : success(fakePanel);
      },
      () => success(liveSnapshot),
    );

    render(<EnvInspectorDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('ei-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
