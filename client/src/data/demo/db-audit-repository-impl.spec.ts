import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { DbAuditApi } from './db-audit-api';
import { DbAuditRepositoryImpl } from './db-audit-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * DbAuditRepositoryImpl spec — fixture-driven: both halves round-trip
 * (committed change + its audit row, rolled-back zero count), the
 * history array parses, malformed payloads resolve as Failed Results.
 */

const AUDIT_URL = '/api/demo/db/audit';

const payload = {
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
    failure: 'violates check constraint "ck_posts_title_length"',
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
  reasoning: 'Measured, not claimed.',
};

function makeRepository(): DbAuditRepositoryImpl {
  return new DbAuditRepositoryImpl(new DbAuditApi(createAppConfig()));
}

describe('DbAuditRepositoryImpl', () => {
  it('fetches and parses both halves with the history', async () => {
    stubApiFetch([{ url: AUDIT_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().prove();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.committed.auditRow.id).toBe(16);
      expect(result.value.rolledBack.auditRowsAdded).toBe(0);
      expect(result.value.history).toHaveLength(1);
      expect(result.value.historyCount).toBe(1);
    }
  });

  it('rejects a payload whose history event lacks the actor', async () => {
    const poisoned = {
      ...payload,
      history: [{ id: 16, occurredAt: '…', action: 'update', changes: '{}' }],
    };
    stubApiFetch([{ url: AUDIT_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().prove();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().prove();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
