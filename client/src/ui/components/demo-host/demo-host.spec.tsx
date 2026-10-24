import { describe, expect, it } from 'vitest';
import { lazy } from 'react';
import { render, screen } from '@testing-library/react';
import { DemoHost } from './demo-host';
import { demoRegistry } from '../../demos/demo-registry';

/**
 * DemoHost spec — the live registry is EMPTY until Phase 3's first demos land,
 * so the known-demo path is proven with a fixture registry (the same
 * `DemoRegistry` contract the live one grows into), and the unknown path with
 * the live one.
 */

const fixtureRegistry = {
  'py:runtime-types': lazy(() =>
    Promise.resolve({
      default: function FixtureDemo() {
        return <p data-testid="fixture-demo-body">the fixture demo body</p>;
      },
    }),
  ),
};

describe('DemoHost', () => {
  it('renders the panel title and description around the registered demo body', async () => {
    render(
      <DemoHost
        demoId="py:runtime-types"
        title="Types at runtime"
        description="Watch type hints behave at runtime."
        registry={fixtureRegistry}
      />,
    );

    expect(
      screen.getByRole('heading', { level: 3, name: 'Types at runtime' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Watch type hints behave at runtime.')).toBeInTheDocument();
    expect(await screen.findByTestId('fixture-demo-body')).toHaveTextContent(
      'the fixture demo body',
    );
  });

  it('renders the friendly not-wired-yet card for a demo id missing from the registry', () => {
    render(<DemoHost demoId="nope:not-built-yet" title="A demo that does not exist" />);

    const card = screen.getByTestId('demo-not-wired');
    expect(card).toBeInTheDocument();
    expect(card).toHaveTextContent('demo not wired yet');
    expect(card).toHaveTextContent('demoId: nope:not-built-yet');
    // It is a note, not an error.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('the live registry holds exactly the demos that have landed', () => {
    // Grows topic by topic (Phase 3+: one lazy entry per demo block id);
    // unknown ids still degrade to the friendly card above.
    expect(Object.keys(demoRegistry)).toEqual([
      'py:runtime-types',
      'runtime:async',
      'runtime:streaming',
      'http:headers',
      'fastapi:app-info',
      'pyd:lab',
      'dep:lifecycle',
      'dep:matrix',
      'routing:explorer',
      'middleware:pipeline',
      'reqres:inspector',
      'reqres:methods',
      'validation:arena',
      'api:posts-workbench',
      'api:docs-link',
      'api:graphql-playground',
      'api:webhook-simulator',
      'api:grpc-console',
      'db:schema-explorer',
      'db:uuid',
      'db:sql-safety',
      'db:migrations',
      'db:sql-lab',
      'db:search',
      'db:race',
      'db:audit',
      'db:orm-probe',
      'db:mongo-console',
      'redis:playground',
      'caching:lab',
      'msg:stream',
      'msg:outbox',
      'auth:sessions',
      'auth:api-keys',
      'auth:jwt',
      'auth:oauth',
      'auth:hashing',
      'auth:refresh',
      'authz:matrix',
      'security:lab',
      'security:pii',
      'files:workbench',
      'i18n:negotiator',
      'realtime:ticker',
      'realtime:chat',
      'jobs:console',
      'errors:explorer',
      'deps:manifest',
      'arch:tracer',
      'obs:viewer',
      'obs:trace',
      'testing:runner',
      'debug:stall',
      'env:inspector',
      'deploy:stack',
      'perf:bench',
      'reliability:breaker',
      'scaling:stateless',
      'best:checklist',
    ]);
  });
});
