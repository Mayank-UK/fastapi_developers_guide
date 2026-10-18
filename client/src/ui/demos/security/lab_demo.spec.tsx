import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { LabDemo } from './lab_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetSecurityLabDemoUseCase } from '../../../domain/demo/get-security-lab-demo-usecase';
import type {
  BurnResult,
  SecurityLabLoad,
} from '../../../domain/demo/security-lab';

/**
 * LabDemo spec — fixture-driven (happy + failure): the panel renders the
 * header table with the OBSERVED live values beside the WHY, the CORS
 * policy with its misconfig note, and the burner's policy; the burn round
 * appends the remaining budget until the typed 429 throttle lands (with
 * its Retry-After); a failed panel degrades to the shared error panel
 * with recovery.
 */

const load: SecurityLabLoad = {
  panel: {
    headers: [
      {
        header: 'X-Content-Type-Options',
        value: 'nosniff',
        why: 'the browser must not second-guess the content type',
      },
      {
        header: 'Strict-Transport-Security',
        value: 'max-age=31536000 — https requests only',
        why: 'https-only after one visit; dev is http',
      },
    ],
    cors: {
      allowedOrigins: ['http://localhost:5174'],
      allowCredentials: true,
      allowedMethods: ['GET', 'POST'],
      allowedHeaders: ['authorization', 'content-type'],
      preflightMaxAgeS: 600,
      misconfigNote: 'wildcard origins with credentials is the classic misconfig',
    },
    rateLimit: {
      windowSeconds: 10,
      budget: 5,
      keying: 'client ip + route',
      burnEndpoint: '/api/demo/security/rate-limit/burn',
      whyPublicEndpoints: 'endpoints that check no credential are the ones anyone may hammer',
    },
    reasoning: 'Three defaults with teeth.',
  },
  observedHeaders: {
    'x-content-type-options': 'nosniff',
    'x-frame-options': 'DENY',
  },
};

const allowedBurn: BurnResult = {
  kind: 'allowed',
  outcome: { attempt: 1, remaining: 4, limit: 5, windowSeconds: 10, detail: '4 of 5 left' },
};

const throttledBurn: BurnResult = {
  kind: 'throttled',
  throttled: {
    status: 429,
    retryAfterSeconds: 7,
    message: 'rate limit exceeded — 5 requests per 10s; retry in 7s',
  },
};

type Stubs = {
  panel?: () => Promise<Result<SecurityLabLoad>>;
  burn?: () => Promise<Result<BurnResult>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetSecurityLabDemoUseCase, {
    panel: stubs.panel ?? (async () => success(load)),
    burn: stubs.burn ?? (async () => success(allowedBurn)),
  } as unknown as GetSecurityLabDemoUseCase);
}

describe('LabDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['security:lab']).toBeDefined();
  });

  it('renders the header table with the observed live values and the cors policy', async () => {
    stubUseCase({});
    render(<LabDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('security-lab-headers')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('security-lab-headers')).toHaveTextContent(
      'X-Content-Type-Options',
    );
    expect(screen.getByTestId('security-lab-headers')).toHaveTextContent('live: nosniff');
    expect(screen.getByTestId('security-lab-headers')).toHaveTextContent(
      '(not on this response',
    );
    expect(screen.getByTestId('security-lab-cors')).toHaveTextContent(
      'http://localhost:5174',
    );
    expect(screen.getByTestId('security-lab-cors')).toHaveTextContent('classic misconfig');
    expect(screen.getByTestId('security-lab-burn')).toHaveTextContent('5 per 10s');
  });

  it('burns: remaining budget first, then the typed 429 with its Retry-After', async () => {
    let calls = 0;
    stubUseCase({
      burn: async () => {
        calls += 1;
        return success(calls < 3 ? allowedBurn : throttledBurn);
      },
    });
    render(<LabDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('security-lab-cors')).toBeInTheDocument(),
    );

    const burnButton = () => screen.getByRole('button', { name: 'burn one unit' });
    burnButton().click();
    await waitFor(() =>
      expect(screen.getAllByTestId('security-lab-burn-entry')).toHaveLength(1),
    );
    expect(screen.getAllByTestId('security-lab-burn-entry')[0]).toHaveTextContent(
      'hit 1: 200 · 4 left',
    );

    burnButton().click();
    await waitFor(() =>
      expect(screen.getAllByTestId('security-lab-burn-entry')).toHaveLength(2),
    );
    burnButton().click();
    await waitFor(() =>
      expect(screen.getAllByTestId('security-lab-burn-entry')).toHaveLength(3),
    );
    expect(screen.getAllByTestId('security-lab-burn-entry')[2]).toHaveTextContent('429');
    expect(screen.getAllByTestId('security-lab-burn-entry')[2]).toHaveTextContent(
      'retry-after 7s',
    );
    expect(screen.getByTestId('security-lab-throttled')).toHaveTextContent(
      'the handler never ran',
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
                requestId: 'req-s1',
              }),
            )
          : success(load);
      },
    });
    render(<LabDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('security-lab-headers')).toBeInTheDocument(),
    );
  });
});
