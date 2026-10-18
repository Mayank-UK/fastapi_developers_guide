import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SchemaExplorerDemo } from './schema_explorer_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetSchemaExplorerDemoUseCase } from '../../../domain/demo/get-schema-explorer-demo-usecase';
import type { SchemaExplorer } from '../../../domain/demo/schema-explorer';

/**
 * SchemaExplorerDemo spec — fixture-driven (happy + drill + failure):
 * the component resolves its use case through the container, so the
 * spec swaps the token registration. Behavior: the roster lists the
 * live tables, clicking a table re-fetches with the focus anatomy
 * (columns/defaults, FK ON DELETE, partial index WHERE), and failures
 * degrade to the shared error panel with recovery.
 */

const roster: SchemaExplorer = {
  databaseName: 'guide',
  tableCount: 5,
  tables: [
    { name: 'authors', columnCount: 5, foreignKeyCount: 0, checkCount: 0, indexCount: 2 },
    { name: 'posts', columnCount: 9, foreignKeyCount: 1, checkCount: 2, indexCount: 4 },
  ],
  reasoning: 'Introspected live from PostgreSQL.',
};

const drilled: SchemaExplorer = {
  ...roster,
  focus: {
    name: 'posts',
    columns: [
      { name: 'id', type: 'bigint', nullable: false, defaultValue: "nextval('posts_id_seq'::regclass)" },
      { name: 'title', type: 'text', nullable: false },
    ],
    primaryKey: ['id'],
    foreignKeys: [
      {
        name: 'fk_posts_author_id_authors',
        columns: ['author_id'],
        referencesTable: 'authors',
        referencesColumns: ['id'],
        onDelete: 'RESTRICT',
      },
    ],
    checks: [{ name: 'ck_posts_status_domain', definition: "CHECK ((status)::text = ANY (...))" }],
    indexes: [
      { name: 'pk_posts', columns: ['id'], kind: 'btree', unique: true, primary: true },
      {
        name: 'ix_posts_published_created_at',
        columns: ['created_at'],
        kind: 'btree',
        unique: false,
        primary: false,
        where: "(status = 'published'::text)",
      },
    ],
  },
};

function stubUseCase(
  rosterResult: () => Promise<Result<SchemaExplorer>>,
  drillResult: (table: string) => Promise<Result<SchemaExplorer>>,
): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetSchemaExplorerDemoUseCase, {
    roster: rosterResult,
    drill: drillResult,
  } as unknown as GetSchemaExplorerDemoUseCase);
}

describe('SchemaExplorerDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:schema-explorer']).toBeDefined();
  });

  it('renders loading first, then the live roster with table buttons', async () => {
    stubUseCase(async () => success(roster), async () => success(drilled));

    render(<SchemaExplorerDemo />);

    expect(screen.getByTestId('se-loading')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('se-roster')).toBeInTheDocument());

    expect(screen.getByTestId('se-roster')).toHaveTextContent('guide');
    const buttons = screen.getAllByTestId('se-table-btn');
    expect(buttons).toHaveLength(2);
    expect(buttons[1]).toHaveTextContent('posts');
    expect(screen.queryByTestId('se-focus')).not.toBeInTheDocument();
    expect(screen.getByTestId('se-reasoning')).toHaveTextContent('PostgreSQL');
  });

  it('drills into a table on click and renders the full anatomy', async () => {
    let drilledInto: string | null = null;
    stubUseCase(
      async () => success(roster),
      async (table) => {
        drilledInto = table;
        return success(drilled);
      },
    );

    render(<SchemaExplorerDemo />);

    const postsButton = await waitFor(() => {
      const buttons = screen.getAllByTestId('se-table-btn');
      const button = buttons.find((b) => b.textContent?.includes('posts'));
      expect(button).toBeDefined();
      return button as HTMLElement;
    });
    postsButton.click();

    await waitFor(() => expect(screen.getByTestId('se-focus')).toBeInTheDocument());
    expect(drilledInto).toBe('posts');

    const rows = screen.getAllByTestId('se-col-row');
    expect(rows).toHaveLength(2);
    expect(screen.getByTestId('se-focus')).toHaveTextContent("nextval('posts_id_seq'::regclass)");
    expect(screen.getByTestId('se-fks')).toHaveTextContent('ON DELETE RESTRICT');
    expect(screen.getByTestId('se-indexes')).toHaveTextContent("where (status = 'published'::text)");
    expect(screen.getByTestId('se-checks')).toHaveTextContent('ck_posts_status_domain');
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(
      async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('PostgreSQL is unreachable.', {
                code: 'service_unavailable',
                status: 503,
                requestId: 'req-16',
              }),
            )
          : success(roster);
      },
      async () => success(drilled),
    );

    render(<SchemaExplorerDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('se-roster')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
