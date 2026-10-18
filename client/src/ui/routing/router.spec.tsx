import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { ThemeProvider } from '../design-system/theme-provider';
import { appRoutes } from './router';
import { RoutePaths, topicPath } from './routes';
import { container } from '../../core/container';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch } from '../../test/fetch_stub';

/**
 * Routing spec — drives the REAL route tree (appRoutes + RootLayout + the lazy
 * home view behind the single Suspense boundary) through an equivalent memory
 * router: the unknown-route degradation and the lazy home view both prove the
 * shell wiring, not just the view components.
 */

beforeAll(() => {
  container.initialize(createAppConfig());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderAt(path: string) {
  const router = createMemoryRouter(appRoutes(), { initialEntries: [path] });
  return render(
    <ThemeProvider>
      <RouterProvider router={router} />
    </ThemeProvider>,
  );
}

describe('routing', () => {
  it('renders the friendly not-found view for an unknown route', async () => {
    renderAt('/nowhere/at/all');

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Page not found' }),
    ).toBeInTheDocument();
    expect(screen.getByText('The page you are looking for does not exist.')).toBeInTheDocument();
    // The shared chrome (guide name + theme toggle) stays present.
    expect(screen.getByRole('link', { name: /FastAPI Developers Guide/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /switch to/i })).toBeInTheDocument();
  });

  it('lazy-loads the home view behind the single Suspense boundary', async () => {
    stubApiFetch([
      { url: '/api/health', body: { status: 'ok', env: 'dev' } },
      { url: '/api/content', body: { version: 1, groups: [], topics: [] } },
    ]);

    renderAt(RoutePaths.Home);

    // The chunk resolves; then the home hero takes over from the fallback.
    expect(
      await screen.findByRole('heading', { level: 1, name: 'FastAPI Developers Guide' }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId('curriculum-landing-soon')).toBeInTheDocument();
  });

  it('lazy-loads the topic view for /topics/:topicId and renders the served topic', async () => {
    stubApiFetch([
      {
        url: '/api/content/pydantic',
        body: {
          version: 1,
          id: 'pydantic',
          title: 'Pydantic',
          group: 'framework',
          order: 5,
          sections: [
            { id: 's1', title: 'The section', blocks: [{ kind: 'text', id: 'b1', text: 'The body.' }] },
          ],
        },
      },
    ]);

    renderAt(topicPath('pydantic'));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Pydantic' }),
    ).toBeInTheDocument();
    expect(screen.getByText('The body.')).toBeInTheDocument();
  });
});
