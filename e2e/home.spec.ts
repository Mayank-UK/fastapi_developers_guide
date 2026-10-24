import { expect, test } from '@playwright/test';

/** The nine group titles the content API serves — the home map shows them all. */
const GROUP_TITLES = [
  'Foundations',
  'Framework',
  'Request handling',
  'APIs',
  'Data',
  'State & auth',
  'Media & realtime',
  'Platform',
  'Capstones',
] as const;

/** Authored topics registered server-side (planned topics arrive as extra
 * "coming soon" cards that are NOT links). 34 → 41 with the wrap-up wave
 * (topics 31/33/35/37/38/39/40 authored, 41/43 live). */
const AUTHORED_TOPIC_LINKS = 41;

/**
 * Home is the guide's front door: a hero with the live health chip and the
 * curriculum index (topic map) fetched live from GET /api/content. This
 * spec pins that the map actually renders in a real browser — every served
 * group, every authored topic as a populated link card, and the planned
 * topics as inert coming-soon cards.
 */
test('the home hub renders the full topic map', async ({ page }) => {
  await page.goto('/');

  // Scoped to the main region: the page-level h1 is the hero inside <main>.
  await expect(
    page
      .getByRole('main')
      .getByRole('heading', { level: 1, name: 'FastAPI Developers Guide' }),
  ).toBeVisible();

  // The map arrives from the content API — wait for the real section to
  // replace the loading skeleton.
  const topicMap = page.locator('#topic-map');
  await expect(topicMap).toBeVisible();

  for (const title of GROUP_TITLES) {
    await expect(topicMap.getByRole('heading', { name: title, exact: true })).toBeVisible();
  }

  // Every authored topic is a populated link; the count pins the map's
  // completeness (a dropped or doubled topic fails here).
  await expect(topicMap.getByRole('link')).toHaveCount(AUTHORED_TOPIC_LINKS);

  // Spot checks: the first authored topic, and one planned topic rendered
  // as an inert coming-soon card (no link, no route). Pinned to
  // third-party (topic 42, one of the two still-unauthored) — deployment
  // got authored in the wrap-up wave (41/43 live) and renders as a link.
  await expect(
    topicMap.getByRole('link', { name: /The Python language/ }),
  ).toBeVisible();
  const plannedCard = topicMap.locator(
    '[data-testid="topic-card-third-party"]',
  );
  await expect(plannedCard).toBeVisible();
  await expect(plannedCard).toHaveAttribute('aria-disabled', 'true');
  await expect(plannedCard.getByText('coming soon', { exact: true })).toBeVisible();
});
