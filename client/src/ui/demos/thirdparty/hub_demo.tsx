import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetThirdPartyHubDemoUseCase } from '../../../domain/demo/get-thirdparty-hub-demo-usecase';
import type {
  DecisionRow,
  IntegrationRow,
  QuotaRow,
  SecretRow,
  ThirdPartyHubPanel,
} from '../../../domain/demo/thirdparty-hub';

/**
 * ThirdPartyHubDemo — the third-party topic's live hub panel (demo
 * block id `thirdparty:hub`). One read where the server lays out
 * everything the app uses that it did not build: the integrate-vs-build
 * walk with every row verified (the manifest parse, the server-tree
 * file checks), the real integration inventory with each dependency's
 * honest failure mode, the key/secret surface as names and blast radii
 * — never values, the builder never reads one — and the real quotas,
 * live reads beside declared constants.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: ThirdPartyHubPanel };

function choiceTone(row: DecisionRow): string {
  return row.choice === 'integrate' ? 'text-primary' : 'text-on-surface-variant';
}

function kindTone(row: IntegrationRow): string {
  if (row.kind === 'backing-service') return 'text-primary';
  if (row.kind === 'machine-auth' || row.kind === 'auth-flow') return 'text-error';
  return 'text-on-surface-variant';
}

function DecisionLine({ row }: { row: DecisionRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`tp-d-${row.id}`}>
      <span className={choiceTone(row)}>[{row.choice}]</span> {row.subject} —{' '}
      <span className="text-on-surface-variant">{row.verified}</span>
    </p>
  );
}

function IntegrationLine({ row }: { row: IntegrationRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`tp-i-${row.id}`}>
      <span className={kindTone(row)}>{row.kind}</span> {row.name} — {row.detail}.{' '}
      <span className="text-on-surface-variant">down: {row.whenDown}</span>
      <br />
      <span className="text-on-surface-variant">evidence: {row.evidence}</span>
    </p>
  );
}

function SecretLine({ row }: { row: SecretRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`tp-s-${row.id}`}>
      <span className="text-error">{row.envVar}</span> — {row.blastRadius}.{' '}
      <span className="text-on-surface-variant">handling: {row.handling}</span>
    </p>
  );
}

function QuotaLine({ row }: { row: QuotaRow }) {
  return (
    <p className="font-mono text-caption text-on-surface" data-testid={`tp-q-${row.id}`}>
      <span className="text-primary">{row.quota}</span> ({row.source}) — {row.atCeiling}
    </p>
  );
}

export default function ThirdPartyHubDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetThirdPartyHubDemoUseCase = container.getThirdPartyHubDemoUseCase;
    const result: Result<ThirdPartyHubPanel> = await useCase.hub();
    if (result.ok) {
      setPanel({ state: 'ready', data: result.value });
    } else {
      setPanel({ state: 'failed', failure: result.failure });
    }
  }, []);

  useEffect(() => {
    void loadPanel();
  }, [loadPanel]);

  if (panel.state === 'loading') {
    return <p data-testid="tp-loading">Auditing what this app did not build…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the third-party hub"
        failure={panel.failure}
        onRetry={() => {
          setPanel({ state: 'loading' });
          void loadPanel();
        }}
      />
    );
  }

  const data = panel.data;

  return (
    <section className="flex flex-col gap-sm" data-testid="tp-panel">
      <section className="flex flex-col gap-xxs" data-testid="tp-decisions">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Integrate vs build</span>{' '}
          <span className="text-on-surface-variant">
            every decision this repo made, verified against the manifest and the tree
          </span>
        </p>
        {data.decisions.map((row) => (
          <DecisionLine key={row.id} row={row} />
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="tp-integrations"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">The real integration inventory</span>{' '}
          <span className="text-on-surface-variant">
            what this app stands on, and what its failure does
          </span>
        </p>
        {data.integrations.map((row) => (
          <IntegrationLine key={row.id} row={row} />
        ))}
      </section>

      <section
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        data-testid="tp-secrets"
      >
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Keys and blast radius</span>{' '}
          <span className="text-on-surface-variant">
            names, scopes, and radii — the values are never read, so they never render
          </span>
        </p>
        {data.secrets.map((row) => (
          <SecretLine key={row.id} row={row} />
        ))}
      </section>

      <section className="flex flex-col gap-xxs" data-testid="tp-quotas">
        <p className="text-caption text-on-surface">
          <span className="font-mono text-primary">Quotas</span>{' '}
          <span className="text-on-surface-variant">
            live reads beside declared constants — the behavior at every ceiling
          </span>
        </p>
        {data.quotas.map((row) => (
          <QuotaLine key={row.id} row={row} />
        ))}
      </section>

      <p className="text-caption text-on-surface-variant" data-testid="tp-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
