import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SqlSafetyDemo } from './sql_safety_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetSqlSafetyDemoUseCase } from '../../../domain/demo/get-sql-safety-demo-usecase';
import type { SqlSafety } from '../../../domain/demo/sql-safety';

/**
 * SqlSafetyDemo spec — fixture-driven (happy + failure): the executed
 * safe card (bind parameter, row count, matched posts), the rendered
 * unsafe card (executed false, spliced SQL on screen), and failures
 * degrade to the shared error panel with recovery.
 */

const payload: SqlSafety = {
  filterValue: "'; DROP TABLE posts; --",
  safe: {
    sql: 'SELECT p.id FROM posts AS p WHERE p.title ILIKE :pattern ORDER BY p.id',
    parameterName: 'pattern',
    parameterValue: "%'; DROP TABLE posts; --%",
    rowCount: 0,
    rows: [],
    note: 'The value traveled as the bind parameter.',
  },
  unsafe: {
    template: "…ILIKE '%{value}%'…",
    renderedSql:
      "SELECT id FROM posts WHERE title ILIKE '%'; DROP TABLE posts; --%' ORDER BY id",
    executed: false,
    why: 'Rendered, never executed.',
  },
  wildcardNote: 'Parameterization stops injection, not LIKE wildcards.',
  reasoning: 'One input, two meanings.',
};

function stubUseCase(result: () => Promise<Result<SqlSafety>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetSqlSafetyDemoUseCase, {
    run: result,
  } as unknown as GetSqlSafetyDemoUseCase);
}

describe('SqlSafetyDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:sql-safety']).toBeDefined();
  });

  it('renders the executed safe card beside the rendered unsafe card', async () => {
    stubUseCase(async () => success(payload));

    render(<SqlSafetyDemo />);

    expect(screen.getByTestId('safety-loading')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('safety-safe')).toBeInTheDocument());

    expect(screen.getByTestId('safety-row-count')).toHaveTextContent('0 row(s)');
    expect(screen.getByTestId('safety-unsafe')).toHaveTextContent('executed: false');
    expect(screen.getByTestId('safety-rendered')).toHaveTextContent('DROP TABLE posts');
    expect(screen.getByTestId('safety-wildcard')).toHaveTextContent('LIKE wildcards');
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
              requestId: 'req-17',
            }),
          )
        : success(payload);
    });

    render(<SqlSafetyDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('safety-safe')).toBeInTheDocument());
  });
});
