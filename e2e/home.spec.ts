import { expect, test } from '@playwright/test';

/** The ten group titles the content API serves — the home map shows them all. */
const GROUP_TITLES = [
  'Foundations',
  'Framework',
  'Request handling',
  'APIs',
  'Data',
  'State & auth',
  'Media & realtime',
  'Platform',
  'Ship',
  'Capstones',
] as const;

/** Authored topics registered server-side. All 43 curriculum topics are
 * authored and the client's planned-topics map is retired, so every card
 * in the map is a populated link — nothing renders as coming soon. */
const AUTHORED_TOPIC_LINKS = 43;

/**
 * Home is the guide's front door: a hero with the live health chip and the
 * curriculum index (topic map) fetched live from GET /api/content. This
 * spec pins that the map actually renders in a real browser — every served
 * group and every topic as a populated link card, with the planned-card
 * machinery gone: zero coming-soon cards render anywhere.
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

  // Spot check: the first authored topic renders as a populated link.
  await expect(
    topicMap.getByRole('link', { name: /The Python language/ }),
  ).toBeVisible();

  // The planned-card machinery is retired from the client entirely: with
  // all 43 topics authored, NO disabled coming-soon cards render anywhere.
  // The disabled TopicCard branch survives only as the served-but-empty
  // defensive path, so a count of zero pins its dormancy.
  await expect(
    topicMap.locator('[data-testid^="topic-card-"][aria-disabled="true"]'),
  ).toHaveCount(0);
});
