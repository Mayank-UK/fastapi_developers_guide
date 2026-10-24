import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import DeployStackDemo from './stack_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDeployStackDemoUseCase } from '../../../domain/demo/get-deploy-stack-demo-usecase';
import type { DeployStackPanel } from '../../../domain/demo/deploy-stack';

/**
 * DeployStackDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the
 * token registration (the container's documented replace-a-singleton
 * seam) instead of stubbing fetch. Behavior, not implementation: the
 * panel renders the runtime facts, the per-area rows with verdict +
 * evidence (and manual rows saying why), and the honesty note; a failed
 * read degrades to the shared error panel with recovery.
 */

const fakePanel: DeployStackPanel = {
  runtime: [
    { id: 'env', label: 'FDG_ENV this process booted in', value: 'dev' },
    { id: 'python', label: 'interpreter', value: '3.13.11' },
    { id: 'pid', label: 'process id', value: '4242' },
    {
      id: 'command',
      label: 'server command line',
      value: '.venv/bin/uvicorn guide.main:app --reload --host 0.0.0.0 --port 8000',
    },
    {
      id: 'graceful-shutdown',
      label: 'graceful-shutdown budget (--timeout-graceful-shutdown)',
      value: 'absent from this process\u2019s argv \u2014 this command runs without it',
    },
    { id: 'workers', label: 'worker processes', value: '1 (default; no --workers flag)' },
    { id: 'reload', label: '--reload (dev hot reload)', value: 'present (--reload \u2014 a DEV-only flag)' },
    {
      id: 'health',
      label: 'real internal GET /api/health',
      value: '200 {"status":"ok","env":"dev"} in 1.4ms',
    },
  ],
  areas: [
    {
      id: 'platform',
      title: 'Platform',
      note: 'docker-compose.platform.yml \u2014 the datastores that outlive every release.',
      items: [
        {
          id: 'platform-services',
          claim: 'The persistent platform carries exactly three datastores \u2014 postgres, redis, mongo',
          checkKind: 'file',
          verdict: 'pass',
          evidence: ['.docker/docker-compose-platform.yml: 4/4 markers found'],
        },
        {
          id: 'image-pins',
          claim: 'Datastore images are pinned',
          checkKind: 'manual',
          verdict: 'manual',
          evidence: [],
          whyManual:
            'the file lives at the repo root (.docker/docker-compose.platform.yml) and is not visible from this process',
        },
      ],
    },
    {
      id: 'kubernetes',
      title: 'Kubernetes',
      note: 'The honest absence \u2014 and what the concepts map onto when it\u2019s time.',
      items: [
        {
          id: 'k8s-manifests',
          claim: 'No Kubernetes manifests ship in this repo',
          checkKind: 'file',
          verdict: 'pass',
          evidence: ['deploy/k8s/: does not exist in the repo (checked at request time)'],
        },
      ],
    },
  ],
  honestyNote: 'Every row was computed at request time.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<DeployStackPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDeployStackDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetDeployStackDemoUseCase);
}

describe('DeployStackDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['deploy:stack']).toBeDefined();
  });

  it('renders the runtime facts and the area rows with verdict + evidence', async () => {
    stubUseCase(() => success(fakePanel));

    render(<DeployStackDemo />);

    await waitFor(() => expect(screen.getByTestId('dsk-panel')).toBeInTheDocument());
    const runtime = screen.getByTestId('dsk-runtime');
    expect(runtime).toHaveTextContent('FDG_ENV this process booted in: dev');
    expect(runtime).toHaveTextContent('.venv/bin/uvicorn guide.main:app --reload');
    expect(runtime).toHaveTextContent('{"status":"ok","env":"dev"}');

    expect(screen.getByTestId('dsk-area-platform')).toHaveTextContent(
      'the datastores that outlive every release',
    );
    const services = screen.getByTestId('dsk-item-platform-services');
    expect(services).toHaveTextContent('pass');
    expect(services).toHaveTextContent('[file]');
    expect(services).toHaveTextContent('4/4 markers found');

    const pins = screen.getByTestId('dsk-item-image-pins');
    expect(pins).toHaveTextContent('manual');
    expect(screen.getByTestId('dsk-why-image-pins')).toHaveTextContent(
      'not visible from this process',
    );

    expect(screen.getByTestId('dsk-item-k8s-manifests')).toHaveTextContent(
      'does not exist in the repo',
    );
    expect(screen.getByTestId('dsk-honesty-note')).toHaveTextContent('computed at request time');
  });

  it('degrades a failed read to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The deploy panel did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-deploy-stack-1',
            }),
          )
        : success(fakePanel);
    });

    render(<DeployStackDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('dsk-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
