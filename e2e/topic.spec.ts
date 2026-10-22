import { expect, test } from '@playwright/test';

/**
 * One topic page, rendered end-to-end: the client's generic TopicView turns
 * the served JSON (topic → sections → blocks) into the real DOM. This spec
 * pins the anatomy facts every topic page promises — sections render, code
 * blocks start COLLAPSED (and expand to the real served source), the
 * terminal companion closes the page, and the live-demo panel mounts.
 */
test('a topic page renders sections, collapsed code, and its live-demo panel', async ({
  page,
}) => {
  await page.goto('/topics/python-language');

  // The served topic title is the page h1, scoped to the article.
  await expect(
    page
      .getByRole('article')
      .getByRole('heading', { level: 1, name: 'The Python language' }),
  ).toBeVisible();

  // Sections render from the content API — the opening pitch, the
  // self-contained basics sections, and the terminal companion that closes
  // every topic.
  await expect(
    page.getByRole('heading', { level: 2, name: 'Why Python on the server' }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', {
      level: 2,
      name: 'Python basics: control flow, loops, functions, classes',
    }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', {
      level: 2,
      name: 'Built-in data structures and strings',
    }),
  ).toBeVisible();
  await expect(
    page
      .getByRole('article')
      .getByRole('heading', { level: 2, name: 'Terminal companion: the curl tour' }),
  ).toBeVisible();

  // Code blocks start collapsed: the language toggle is aria-expanded=false
  // and the source itself is not in the DOM until clicked. The first toggle
  // on the page is the dependency manifest ("toml") quoting pyproject.toml.
  const tomlToggle = page.getByRole('button', { name: 'toml', exact: true }).first();
  await expect(tomlToggle).toHaveAttribute('aria-expanded', 'false');
  const tomlSource = page.locator('figure', { has: tomlToggle }).locator('pre');
  await expect(tomlSource).toHaveCount(0);

  // Expanding reveals the real served code — the guide package manifest.
  await tomlToggle.click();
  await expect(tomlToggle).toHaveAttribute('aria-expanded', 'true');
  await expect(tomlSource).toBeVisible();
  await expect(tomlSource).toContainText('name = "guide"');

  // The live-demo panel mounts (the demo body lazy-loads; the panel heading
  // comes from the served content, so it is the stable mount signal).
  await expect(
    page.getByRole('heading', { level: 3, name: 'Types at runtime — the proof' }),
  ).toBeVisible();
});
