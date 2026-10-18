import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DbAuditDemo } from './audit_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDbAuditDemoUseCase } from '../../../domain/demo/get-db-audit-demo-usecase';
import type { AuditDemo } from '../../../domain/demo/db-audit';

/**
 * DbAuditDemo spec — fixture-driven (happy + failure): the committed
 * half shows the change and its audit row, the rolled-back half shows
 * zero rows added and the real error, the history grows per run, and
 * failures degrade to the shared error panel with recovery.
 */

const audit: AuditDemo = {
  postId: 7,
  postTitle: 'The envelope is the error model',
  committed: {
    statusBefore: 'draft',
    statusAfter: 'published',
    changeVisible: true,
    auditRow: {
      id: 16,
      occurredAt: '2026-10-16T10:56:09.833892+00:00',
      actor: 'demo:db-audit',
      action: 'update',
      changes: "{'status': 'status: draft -> published'}",
    },
  },
  rolledBack: {
    attemptedTitle: 'this title is deliberately far too long … (204 characters)',
    failure:
      'new row for relation "posts" violates check constraint "ck_posts_title_length"',
    changeVisible: false,
    auditRowsAdded: 0,
  },
  history: [
    {
      id: 16,
      occurredAt: '2026-10-16T10:56:09.833892+00:00',
      actor: 'demo:db-audit',
      action: 'update',
      changes: "{'status': 'status: draft -> published'}",
    },
  ],
  historyCount: 1,
  reasoning: 'The audit row exists exactly when its change exists.',
};

function stubUseCase(result: () => Promise<Result<AuditDemo>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDbAuditDemoUseCase, {
    run: result,
  } as unknown as GetDbAuditDemoUseCase);
}

describe('DbAuditDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:audit']).toBeDefined();
  });

  it('renders both halves and the growing history', async () => {
    stubUseCase(async () => success(audit));

    render(<DbAuditDemo />);

    await waitFor(() => expect(screen.getByTestId('audit-committed')).toBeInTheDocument());
    expect(screen.getByTestId('audit-committed')).toHaveTextContent('draft → published');
    expect(screen.getByTestId('audit-committed')).toHaveTextContent('audit row #16');
    expect(screen.getByTestId('audit-rolled-back')).toHaveTextContent(
      'audit rows added: 0',
    );
    expect(screen.getByTestId('audit-rolled-back')).toHaveTextContent(
      'ck_posts_title_length',
    );
    expect(screen.getAllByTestId('audit-history-row')).toHaveLength(1);
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('PostgreSQL is unreachable.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-22',
            }),
          )
        : success(audit);
    });

    render(<DbAuditDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('audit-committed')).toBeInTheDocument());
  });
});
