import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { SchemaExplorerApi } from './schema-explorer-api';
import { SchemaExplorerRepositoryImpl } from './schema-explorer-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * SchemaExplorerRepositoryImpl spec — fixture-driven: the roster
 * round-trips (counts, optional fields absent at the root), the
 * drill-down adds the focus anatomy (columns with defaults, partial
 * index WHERE), wire nulls never reach the domain (undefined instead),
 * malformed payloads and non-2xx envelopes resolve as Failed Results.
 */

const ROSTER_URL = '/api/demo/db/schema-explorer';

const rosterPayload = {
  databaseName: 'guide',
  tableCount: 5,
  tables: [
    { name: 'authors', columnCount: 5, foreignKeyCount: 0, checkCount: 0, indexCount: 2 },
    { name: 'posts', columnCount: 9, foreignKeyCount: 1, checkCount: 2, indexCount: 4 },
  ],
  reasoning: 'Introspected live from PostgreSQL.',
};

const focusPayload = {
  ...rosterPayload,
  focus: {
    name: 'posts',
    columns: [
      { name: 'id', type: 'bigint', nullable: false, default: "nextval('posts_id_seq'::regclass)" },
      { name: 'title', type: 'text', nullable: false },
      { name: 'tags', type: 'text[]', nullable: false, default: "'{}'" },
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

function makeRepository(): SchemaExplorerRepositoryImpl {
  return new SchemaExplorerRepositoryImpl(new SchemaExplorerApi(createAppConfig()));
}

describe('SchemaExplorerRepositoryImpl', () => {
  it('fetches the roster with counts and no focus at the root', async () => {
    stubApiFetch([{ url: ROSTER_URL, method: 'GET', body: rosterPayload }]);

    const result = await makeRepository().explorer();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.databaseName).toBe('guide');
      expect(result.value.tableCount).toBe(5);
      expect(result.value.tables[1]).toEqual({
        name: 'posts',
        columnCount: 9,
        foreignKeyCount: 1,
        checkCount: 2,
        indexCount: 4,
      });
      expect(result.value.focus).toBeUndefined();
      expect(result.value.reasoning).toContain('PostgreSQL');
    }
  });

  it('drills into one table, focus anatomy included', async () => {
    stubApiFetch([{ url: `${ROSTER_URL}?table=posts`, method: 'GET', body: focusPayload }]);

    const result = await makeRepository().explorer('posts');

    expect(result.ok).toBe(true);
    if (result.ok) {
      const focus = result.value.focus;
      expect(focus?.columns[0]).toEqual({
        name: 'id',
        type: 'bigint',
        nullable: false,
        defaultValue: "nextval('posts_id_seq'::regclass)",
      });
      // No default on the wire stays undefined, never null.
      expect('defaultValue' in (focus?.columns[1] ?? {})).toBe(false);
      expect(focus?.foreignKeys[0]?.onDelete).toBe('RESTRICT');
      expect(focus?.indexes[1]?.where).toBe("(status = 'published'::text)");
      expect('where' in (focus?.indexes[0] ?? {})).toBe(false);
    }
  });

  it('rejects a payload whose focus is not an object', async () => {
    stubApiFetch([{ url: ROSTER_URL, method: 'GET', body: { ...rosterPayload, focus: 7 } }]);

    const result = await makeRepository().explorer();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards the honest 404 envelope for an unknown table into a Failed Result', async () => {
    stubApiFetch([
      {
        url: `${ROSTER_URL}?table=nope`,
        method: 'GET',
        status: 404,
        body: { error: { code: 'not_found', message: "Table 'nope' does not exist.", requestId: 'r' } },
      },
    ]);

    const result = await makeRepository().explorer('nope');

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('not_found');
      expect(result.failure.status).toBe(404);
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().explorer();

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
