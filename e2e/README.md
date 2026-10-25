# Browser E2E (host-side Playwright)

Three real-browser specs, small on purpose — each pins one wiring fact no
in-process test can see (the rendered page and the nginx → FastAPI proxy
hop):

- `home.spec.ts` — the topic map renders from the content API: all 10 groups,
  43 populated topic links, zero coming-soon cards (the planned-card
  machinery is retired).
- `topic.spec.ts` — a topic page renders: sections, collapsed-by-default
  code blocks, the terminal companion, and a mounted live-demo panel.
- `console.spec.ts` — home + a topic page open with zero console errors.

## Why this runs on the host

The devcontainer's tooling container runs unprivileged, so Chromium's
system libraries cannot be installed there. The suite therefore runs on the
HOST against an externally managed stack — never a `webServer` block. The
default base URL is the production-image CI stack (nginx published on the
loopback by `.docker/docker-compose.ci.yml`); the dev stack works too via
`E2E_BASE_URL=http://localhost:5174`.

## Run it

Prerequisites: host Node 22+, and the production-image stack up (from the
repo root — the platform datastores first, then the app stack with the CI
override):

```bash
docker compose -f .docker/docker-compose-platform.yml up -d --wait
docker compose -f .docker/docker-compose.prod.yml \
  -f .docker/docker-compose.ci.yml up -d --wait

cd e2e
npm ci
npx playwright install chromium
npm test
```

`E2E_BASE_URL` overrides the default `http://127.0.0.1:8080`; CI sets it to
exactly that value when the workflow boots the same stack it just built.
