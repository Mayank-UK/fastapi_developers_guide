import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import BestChecklistDemo from './checklist_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetBestChecklistDemoUseCase } from '../../../domain/demo/get-best-checklist-demo-usecase';
import type { BestChecklistPanel } from '../../../domain/demo/best-checklist';

/**
 * BestChecklistDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the panel
 * renders the score line, verdict badges with their evidence, an honest
 * manual row WITH its why and WITHOUT evidence, the anti-checklist rows,
 * and a failed load degrades to the shared error panel with recovery.
 */

const fakePanel: BestChecklistPanel = {
  areas: [
    {
      id: 'security',
      title: 'Security',
      note: 'Headers, hashing, throttling — never opt-in defaults.',
      items: [
        {
          id: 'security-headers',
          practice: 'Defensive headers on every success response',
          checkKind: 'live',
          verdict: 'pass',
          evidence: [
            'GET /api/health → 200',
            'x-content-type-options: nosniff',
            'x-frame-options: DENY',
          ],
          whyManual: null,
        },
        {
          id: 'headers-on-errors',
          practice: 'Defensive headers on ERROR responses too',
          checkKind: 'live',
          verdict: 'pass',
          evidence: ['the 404 response carried: x-content-type-options: nosniff'],
          whyManual: null,
        },
      ],
    },
    {
      id: 'git-and-review',
      title: 'Git & review',
      note: 'Small diffs, machine checks, and a human who reads.',
      items: [
        {
          id: 'review-your-diffs',
          practice: 'Every diff gets a human read before it lands',
          checkKind: 'manual',
          verdict: 'manual',
          evidence: [],
          whyManual: 'no automation reads a diff\u2019s design intent',
        },
      ],
    },
  ],
  notDones: [
    {
      id: 'no-hosted-ci',
      notDone: 'No hosted CI by default',
      reason: 'Local docker-flock verify one-liners are the only gate.',
      artifacts: ['the verify one-liners — this topic\u2019s terminal companion, stop 4'],
    },
  ],
  summary: { items: 3, passed: 2, failed: 0, manual: 1 },
  honestyNote: 'Every verdict on this panel was computed at request time.',
};

/** Swap the container's use-case token for a stub answering the panel. */
function stubUseCase(respond: () => Result<BestChecklistPanel>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetBestChecklistDemoUseCase, {
    panel: () => Promise.resolve(respond()),
  } as unknown as GetBestChecklistDemoUseCase);
}

describe('BestChecklistDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['best:checklist']).toBeDefined();
  });

  it('renders the score line, live evidence, and the honest manual row', async () => {
    stubUseCase(() => success(fakePanel));

    render(<BestChecklistDemo />);

    await waitFor(() => expect(screen.getByTestId('bc-panel')).toBeInTheDocument());
    expect(screen.getByTestId('bc-summary')).toHaveTextContent('2 passed · 0 failed · 1 manual');
    expect(screen.getByTestId('bc-areas-count')).toHaveTextContent('2 practice areas');

    const liveRow = screen.getByTestId('bc-item-security-headers');
    expect(liveRow).toHaveTextContent('Defensive headers on every success response');
    expect(screen.getByTestId('bc-evidence-security-headers')).toHaveTextContent(
      'x-content-type-options: nosniff',
    );
    expect(screen.getByTestId('bc-verdict-security-headers')).toHaveTextContent('pass');

    const manualRow = screen.getByTestId('bc-item-review-your-diffs');
    expect(manualRow).toHaveTextContent('human read');
    expect(screen.getByTestId('bc-verdict-review-your-diffs')).toHaveTextContent('manual');
    expect(screen.getByTestId('bc-why-review-your-diffs')).toHaveTextContent(
      'no automation reads',
    );
    expect(
      screen.queryByTestId('bc-evidence-review-your-diffs'),
    ).not.toBeInTheDocument();
  });

  it('renders the anti-checklist with reasons and artifacts', async () => {
    stubUseCase(() => success(fakePanel));

    render(<BestChecklistDemo />);

    await waitFor(() => expect(screen.getByTestId('bc-not-dones')).toBeInTheDocument());
    const notDone = screen.getByTestId('bc-not-done-no-hosted-ci');
    expect(notDone).toHaveTextContent('No hosted CI by default');
    expect(notDone).toHaveTextContent('verify one-liners are the only gate');
    expect(notDone).toHaveTextContent('terminal companion, stop 4');
    expect(screen.getByTestId('bc-honesty')).toHaveTextContent('computed at request time');
  });

  it('degrades a failed load to the shared error panel with recovery', async () => {
    let calls = 0;
    stubUseCase(() => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The audit did not answer.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-best-1',
            }),
          )
        : success(fakePanel);
    });

    render(<BestChecklistDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('bc-panel')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
