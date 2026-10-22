import { defineConfig, devices } from '@playwright/test';

/**
 * Browser E2E for the guide — a standalone package (own lockfile) run from
 * the HOST against an EXTERNALLY managed stack, never a devcontainer: the
 * tooling container runs unprivileged, so Chromium's system libraries
 * cannot be installed there.
 *
 * No `webServer` block on purpose: the suite never boots anything itself.
 * The default base URL is the production-image CI stack (nginx published on
 * 127.0.0.1:8080 by .docker/docker-compose.ci.yml) — the same front door
 * the CI workflow probes. Point E2E_BASE_URL at the dev stack (client
 * http://localhost:5174) to drive Vite instead; if a stack is down, start
 * it from the repo root before running:
 *   docker compose -f .docker/docker-compose.platform.yml up -d --wait
 *   docker compose -f .docker/docker-compose.prod.yml \
 *     -f .docker/docker-compose.ci.yml up -d --wait
 */
export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // Deterministic by design: a red e2e test is a wiring signal, and
  // re-rolling it throws the information away. Zero retries, one worker —
  // the specs share a single stack.
  retries: 0,
  workers: 1,
  fullyParallel: false,
  reporter: 'line',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8080',
    headless: true,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
