import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { HomeView } from './home_view';
import { container } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../../test/fetch_stub';

/**
 * HomeView spec — behavior, not implementation: loading → index render,
 * empty-registry degradation, error degradation with retry recovery, and the
 * live health chip. The view resolves use cases through the (real) container;
 * fetch is stubbed.
 */

beforeAll(() => {
  container.initialize(createAppConfig());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const healthOk = { status: 'ok', env: 'dev' };

/** Groups deliberately out of wire order to prove the client sorts by `order`. */
const contentIndex = {
  version: 1,
  groups: [
    { id: 'apis', title: 'APIs', order: 2 },
    { id: 'foundations', title: 'Foundations', order: 1 },
  ],
  topics: [
    { id: 'api-design', title: 'API Design', group: 'apis', order: 1, sectionCount: 0 },
    {
      id: 'python-language',
      title: 'Python Language',
      subtitle: 'Why Python on the server',
      group: 'foundations',
      order: 1,
      sectionCount: 7,
    },
    {
      id: 'fastapi-fundamentals',
      title: 'FastAPI Fundamentals',
      subtitle: 'From uv scaffold to a running app',
      group: 'foundations',
      order: 2,
      sectionCount: 8,
    },
  ],
};

const emptyIndex = { version: 1, groups: [], topics: [] };

/** The nine planned (not-yet-authored) curriculum topic ids. */
const PLANNED_TOPIC_IDS = [
  'dependency-management',
  'observability',
  'debugging',
  'deployment',
  'performance',
  'reliability',
  'scaling',
  'third-party',
  'advanced-architecture',
];

/** The authored tail of the real registry (groups and curriculum orders as
 * served today) — the fixture the planned-topic merge is rendered against. */
const authoredTailIndex = {
  version: 1,
  groups: [
    { id: 'foundations', title: 'Foundations', order: 1 },
    { id: 'platform', title: 'Platform', order: 8 },
    { id: 'capstones', title: 'Capstones', order: 10 },
  ],
  topics: [
    {
      id: 'python-language',
      title: 'Python Language',
      group: 'foundations',
      order: 1,
      sectionCount: 11,
    },
    {
      id: 'exception-handling',
      title: 'Exception handling',
      group: 'platform',
      order: 30,
      sectionCount: 9,
    },
    {
      id: 'architecture',
      title: 'Architecture',
      group: 'platform',
      order: 32,
      sectionCount: 9,
    },
    {
      id: 'testing',
      title: 'Testing',
      group: 'platform',
      order: 34,
      sectionCount: 10,
    },
    {
      id: 'environments',
      title: 'Environments',
      group: 'platform',
      order: 36,
      sectionCount: 7,
    },
    {
      id: 'best-practices',
      title: 'Best practices',
      group: 'capstones',
      order: 41,
      sectionCount: 12,
    },
  ],
};

/** A planned card is a plain (keyboard-inert) div: no anchor, no href, no
 * route — only the coming-soon affordance. */
function expectComingSoonCard(card: HTMLElement): void {
  expect(card.tagName).toBe('DIV');
  expect(card.querySelector('a')).toBeNull();
  expect(card).not.toHaveAttribute('href');
  expect(card).toHaveAttribute('aria-disabled', 'true');
  expect(card).toHaveAttribute('title', 'Coming soon');
  expect(card).toHaveTextContent('coming soon');
}

/** Asserts `after` renders later in the document than `before`. */
function expectFollows(before: HTMLElement, after: HTMLElement): void {
  expect(
    before.compareDocumentPosition(after) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
}

function renderHome() {
  return render(
    <MemoryRouter>
      <HomeView />
    </MemoryRouter>,
  );
}

describe('HomeView', () => {
  it('renders loading first, then the topic map: groups in order, topic links with subtitle + section count, live health chip', async () => {
    stubApiFetch([
      { url: '/api/health', body: healthOk },
      { url: '/api/content', body: contentIndex },
    ]);

    renderHome();

    // Loading state comes first.
    expect(screen.getByTestId('topic-map-loading')).toBeInTheDocument();
    expect(screen.getByTestId('health-chip')).toHaveTextContent('api: checking…');

    // The health chip flips to the served status.
    await waitFor(() =>
      expect(screen.getByTestId('health-chip')).toHaveTextContent('api: ok · dev'),
    );

    // Topic cards arrive: populated ones are links carrying subtitle + count.
    const populated = await screen.findByTestId('topic-card-fastapi-fundamentals');
    expect(populated).toHaveAttribute('href', '/topics/fastapi-fundamentals');
    expect(populated).toHaveTextContent('FastAPI Fundamentals');
    expect(populated).toHaveTextContent('From uv scaffold to a running app');
    expect(populated).toHaveTextContent('8 sections');

    // sectionCount === 0 topics degrade to disabled "soon" cards (no link).
    const soon = screen.getByTestId('topic-card-api-design');
    expect(soon.querySelector('a')).toBeNull();
    expect(soon).toHaveAttribute('aria-disabled', 'true');
    expect(soon).toHaveTextContent('soon');

    // Group display order follows `order`, not wire order.
    const foundations = screen.getByText('Foundations');
    const apis = screen.getByText('APIs');
    expect(
      foundations.compareDocumentPosition(apis) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it('renders the nine planned topics as disabled coming-soon cards: ship reads between platform and capstones, planned entries interleave by curriculum order, authored cards stay links', async () => {
    stubApiFetch([
      { url: '/api/health', body: healthOk },
      { url: '/api/content', body: authoredTailIndex },
    ]);

    renderHome();

    await screen.findByTestId('topic-card-python-language');

    // All nine planned cards render, disabled and non-navigable.
    const plannedCards = PLANNED_TOPIC_IDS.map((id) =>
      screen.getByTestId(`topic-card-${id}`),
    );
    expect(plannedCards).toHaveLength(9);
    for (const card of plannedCards) {
      expectComingSoonCard(card);
    }

    // The six authored cards are untouched: real links to their topic pages.
    for (const id of [
      'python-language',
      'exception-handling',
      'architecture',
      'testing',
      'environments',
      'best-practices',
    ]) {
      const card = screen.getByTestId(`topic-card-${id}`);
      expect(card.tagName).toBe('A');
      expect(card).toHaveAttribute('href', `/topics/${id}`);
      expect(card).not.toHaveAttribute('aria-disabled');
    }

    // The client-only ship group reads between platform and capstones.
    expectFollows(screen.getByText('Platform'), screen.getByText('Ship'));
    expectFollows(screen.getByText('Ship'), screen.getByText('Capstones'));

    // Planned entries interleave with authored ones by curriculum order…
    expectFollows(
      screen.getByTestId('topic-card-exception-handling'),
      screen.getByTestId('topic-card-dependency-management'),
    );
    expectFollows(
      screen.getByTestId('topic-card-dependency-management'),
      screen.getByTestId('topic-card-architecture'),
    );
    expectFollows(
      screen.getByTestId('topic-card-testing'),
      screen.getByTestId('topic-card-debugging'),
    );
    // …including capstones, after the authored best-practices.
    expectFollows(
      screen.getByTestId('topic-card-best-practices'),
      screen.getByTestId('topic-card-third-party'),
    );
    expectFollows(
      screen.getByTestId('topic-card-third-party'),
      screen.getByTestId('topic-card-advanced-architecture'),
    );
  });

  it('renders the friendly landing-soon state for an EMPTY registry (zero topics)', async () => {
    stubApiFetch([
      { url: '/api/health', body: healthOk },
      { url: '/api/content', body: emptyIndex },
    ]);

    renderHome();

    const landing = await screen.findByTestId('curriculum-landing-soon');
    expect(landing).toHaveTextContent('The curriculum is landing soon');
    expect(landing).toHaveTextContent('being authored');
    // No crash, no topic cards, no error panel — and no planned cards either:
    // an empty registry is the landing-soon state, not a preview of the
    // curriculum (the merge only augments a non-empty index).
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByTestId('topic-map-loading')).not.toBeInTheDocument();
    expect(screen.queryByTestId('topic-card-deployment')).not.toBeInTheDocument();
  });

  it('shows the error panel with envelope diagnostics, then recovers when retry re-runs the load', async () => {
    stubApiFetch([
      { url: '/api/health', body: healthOk },
      {
        url: '/api/content',
        status: 500,
        body: {
          error: { code: 'internal', message: 'boom', requestId: 'req-1' },
        },
      },
    ]);

    renderHome();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load the topic map');
    expect(alert).toHaveTextContent('boom');
    expect(alert).toHaveTextContent('internal · status 500 · request req-1');

    // Retry: the second load succeeds and the topic map takes over.
    stubApiFetch([{ url: '/api/content', body: contentIndex }]);
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    expect(
      await screen.findByTestId('topic-card-fastapi-fundamentals'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('degrades the health chip inline when the server is unreachable (status 0)', async () => {
    stubNetworkFailure();

    renderHome();

    await waitFor(() =>
      expect(screen.getByTestId('health-chip')).toHaveTextContent('api: down'),
    );
    // Both the health probe and the topic map fail; the content error is the
    // screen-level alert, the health failure stays in the chip.
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Could not load the topic map');
    expect(alert).toHaveTextContent('Could not reach the server.');
    expect(alert).toHaveTextContent('network_error · status 0');
  });
});
