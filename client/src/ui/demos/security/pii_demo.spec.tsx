import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PiiDemo } from './pii_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetSecurityPiiDemoUseCase } from '../../../domain/demo/get-security-pii-demo-usecase';
import type { GetAuthJwtDemoUseCase } from '../../../domain/demo/get-auth-jwt-demo-usecase';
import type {
  EraseProof,
  ExportedSubject,
  MaskedSubject,
  PiiPanel,
} from '../../../domain/demo/security-pii';

/**
 * PiiDemo spec — fixture-driven (happy + failure): the panel renders the
 * classification catalog and the role→mask table; the viewer select loads
 * the subject AS THAT CALLER (anonymous full mask vs admin raw); export
 * surfaces the 403 reason for a non-admin and the raw record for the
 * admin; erase proves the round with before/after counts; a failed panel
 * degrades to the shared error panel with recovery.
 */

const panel: PiiPanel = {
  subjects: [
    { customerId: 'cust-2f9a41', country: 'EE' },
    { customerId: 'cust-7c1d02', country: 'JP' },
  ],
  classification: [
    {
      field: 'email',
      category: 'contact',
      tier: 'sensitive',
      allowsPartial: true,
      rationale: 'identifies the person and reaches them',
    },
    {
      field: 'national_id',
      category: 'identifier',
      tier: 'regulated',
      allowsPartial: false,
      rationale: 'government identity; no partial form',
    },
  ],
  roleMasks: [
    { role: 'admin', maskLevel: 'none', note: 'sees the raw values' },
    { role: 'viewer', maskLevel: 'full', note: 'sees full masks' },
    { role: '(anonymous)', maskLevel: 'full', note: 'fail-closed default' },
  ],
  storeCount: 2,
  subjectEndpoint: '/api/demo/security/pii/subjects/{subject_id}',
  exportEndpoint: '/api/demo/security/pii/subjects/{subject_id}/export',
  eraseEndpoint: '/api/demo/security/pii/subjects/{subject_id}/erase',
  resetEndpoint: '/api/demo/security/pii/reset',
  minimizationNote: 'the record you never stored cannot leak',
  reasoning: 'Classification, masking, erasure — mechanisms.',
};

const maskedAnonymous: MaskedSubject = {
  customerId: 'cust-2f9a41',
  principal: '(anonymous)',
  principalRole: null,
  maskLevel: 'full',
  fields: [
    {
      field: 'email',
      category: 'contact',
      tier: 'sensitive',
      value: '***',
      masked: true,
      applied: 'full',
    },
    {
      field: 'country',
      category: 'demographic',
      tier: 'internal',
      value: 'EE',
      masked: false,
      applied: 'none',
    },
  ],
  detail: "'(anonymous)' (no role) views 'cust-2f9a41' at mask level 'full'",
};

const maskedAdmin: MaskedSubject = {
  ...maskedAnonymous,
  principal: 'ada',
  principalRole: 'admin',
  maskLevel: 'none',
  fields: [
    {
      field: 'email',
      category: 'contact',
      tier: 'sensitive',
      value: 'marta.ilves@example.org',
      masked: false,
      applied: 'none',
    },
  ],
};

const exported: ExportedSubject = {
  customerId: 'cust-2f9a41',
  principal: 'ada',
  record: {
    customerId: 'cust-2f9a41',
    fullName: 'Marta Ilves',
    email: 'marta.ilves@example.org',
    phone: '+372 55 667 8899',
    dateOfBirth: '1987-03-14',
    nationalId: 'EE-39203178741',
    cardNumber: '4024 0071 4638 2213',
    country: 'EE',
    signupAt: '2026-02-11T09:24:00Z',
  },
  classification: panel.classification,
  detail: 'ada exported the record — data portability',
};

const eraseProof: EraseProof = {
  customerId: 'cust-2f9a41',
  principal: 'ada',
  recordsBefore: 2,
  recordsAfter: 1,
  detail: 'erased with counts as proof',
};

type Stubs = {
  panel?: () => Promise<Result<PiiPanel>>;
  subject?: (customerId: string, credential: unknown) => Promise<Result<MaskedSubject>>;
  exportSubject?: () => Promise<Result<ExportedSubject>>;
  eraseSubject?: () => Promise<Result<EraseProof>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetSecurityPiiDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    subject:
      stubs.subject ??
      (async (_customerId: string, credential: unknown) =>
        success(
          (credential as { token?: string } | null)?.token === 'token-ada'
            ? maskedAdmin
            : maskedAnonymous,
        )),
    exportSubject:
      stubs.exportSubject ??
      (async () =>
        failed(
          new ServerFailure(
            "forbidden — customer data export/erase is admin-only, and 'alan' carries roles ['viewer']",
            { code: 'forbidden', status: 403, requestId: 'req-p1' },
          ),
        )),
    eraseSubject: stubs.eraseSubject ?? (async () => success(eraseProof)),
  } as unknown as GetSecurityPiiDemoUseCase);
  container.register(ContainerTokens.GetAuthJwtDemoUseCase, {
    mint: async (username: string) =>
      success({
        token: `token-${username}`,
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

describe('PiiDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['security:pii']).toBeDefined();
  });

  it('renders the classification catalog and the role mask table', async () => {
    stubUseCase({});
    render(<PiiDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-classification')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('security-pii-classification')).toHaveTextContent(
      'national_id · identifier · regulated · full only',
    );
    expect(screen.getByTestId('security-pii-classification')).toHaveTextContent(
      'admin → none',
    );
    expect(screen.getByTestId('security-pii-classification')).toHaveTextContent(
      '(anonymous) → full',
    );
  });

  it('loads the subject as the anonymous caller at the full mask', async () => {
    stubUseCase({});
    render(<PiiDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-subject')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('security-pii-subject')).toHaveTextContent('(anonymous)');
    expect(screen.getByTestId('security-pii-subject')).toHaveTextContent('email = ***');
    expect(screen.getByTestId('security-pii-subject')).toHaveTextContent('country = EE');
  });

  it('switching to the admin viewer mints a token and shows the raw values', async () => {
    stubUseCase({});
    render(<PiiDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-subject')).toBeInTheDocument(),
    );

    const viewerSelect = screen.getByRole('combobox', { name: 'viewer' }) as HTMLSelectElement;
    viewerSelect.value = 'ada';
    viewerSelect.dispatchEvent(new Event('change', { bubbles: true }));

    await waitFor(() =>
      expect(screen.getByTestId('security-pii-subject')).toHaveTextContent('mask none'),
    );
    expect(screen.getByTestId('security-pii-subject')).toHaveTextContent(
      'marta.ilves@example.org',
    );
  });

  it('export as a non-admin surfaces the 403 reason; as admin the raw record', async () => {
    let exports = 0;
    stubUseCase({
      exportSubject: async () => {
        exports += 1;
        return exports === 1
          ? failed(
              new ServerFailure(
                "forbidden — customer data export/erase is admin-only, and 'alan' carries roles ['viewer']",
                { code: 'forbidden', status: 403, requestId: 'req-p2' },
              ),
            )
          : success(exported);
      },
    });
    render(<PiiDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-subject')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'export as anonymous' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-round-error')).toHaveTextContent(
        'forbidden: forbidden — customer data export/erase is admin-only',
      ),
    );

    const viewerSelect = screen.getByRole('combobox', { name: 'viewer' }) as HTMLSelectElement;
    viewerSelect.value = 'ada';
    viewerSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-subject')).toHaveTextContent('mask none'),
    );

    screen.getByRole('button', { name: 'export as ada' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-round')).toHaveTextContent(
        'exported as ada: marta.ilves@example.org',
      ),
    );
  });

  it('erase proves the round with before/after counts', async () => {
    stubUseCase({});
    render(<PiiDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-subject')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'erase as anonymous' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-round')).toHaveTextContent(
        '2 → 1 records',
      ),
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
                requestId: 'req-p3',
              }),
            )
          : success(panel);
      },
    });
    render(<PiiDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('security-pii-classification')).toBeInTheDocument(),
    );
  });
});
