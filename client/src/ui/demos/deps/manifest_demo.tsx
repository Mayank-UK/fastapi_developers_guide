import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetDepsManifestDemoUseCase } from '../../../domain/demo/get-dep-manifest-demo-usecase';
import type { DepsManifestPanel, DirectDepRow } from '../../../domain/demo/dep-manifest';

/**
 * DepsManifestDemo — the dependency-management topic's panel (demo block
 * id `deps:manifest`). One live parse of the server's REAL
 * server/pyproject.toml + server/uv.lock: the two dependency groups
 * (runtime main vs dev tooling), every direct dependency's manifest range
 * beside the lock's exact pin with an honest satisfied / not-judged
 * verdict, the manifest/lock agreement cross-check, the fastapi-rooted
 * direct-vs-transitive tree slice, and whole-lock counts. A server that
 * could not read its files degrades to an honest unavailable card — the
 * panel never claims what it did not parse.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: DepsManifestPanel };

function Verdict({ row }: { row: DirectDepRow }) {
  if (row.satisfies === null) {
    return (
      <span data-testid={`dm-verdict-${row.name}`} className="text-on-surface-variant">
        [not judged]
      </span>
    );
  }
  const tone = row.satisfies ? 'text-primary' : 'text-error';
  return (
    <span data-testid={`dm-verdict-${row.name}`} className={tone}>
      [{row.satisfies ? 'satisfied' : 'VIOLATED'}]
    </span>
  );
}

export default function DepsManifestDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });

  const loadPanel = useCallback(async () => {
    const useCase: GetDepsManifestDemoUseCase = container.getDepsManifestDemoUseCase;
    const result: Result<DepsManifestPanel> = await useCase.panel();
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
    return <p data-testid="dm-loading">Parsing the real manifest and lock…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the dependency manifest panel"
        failure={panel.failure}
        onRetry={() => {
          setPanel({ state: 'loading' });
          void loadPanel();
        }}
      />
    );
  }

  const data = panel.data;

  if (!data.available) {
    return (
      <section
        data-testid="dm-unavailable"
        className="rounded-md border border-warning px-sm py-xs text-caption text-on-surface"
      >
        <p className="font-mono">
          {data.manifestFile} + {data.lockFile} could not be read by the server:
        </p>
        <p className="font-mono text-warning">{data.unavailableReason}</p>
        <p className="text-on-surface-variant">{data.honestyNote}</p>
      </section>
    );
  }

  const direct = data.direct;
  const main = direct.filter((row) => row.group === 'main');
  const dev = direct.filter((row) => row.group === 'dev');
  const treeSlice = data.slice;

  return (
    <section className="flex flex-col gap-sm" data-testid="dm-panel">
      <header className="flex flex-wrap items-baseline gap-x-sm gap-y-xxs">
        <p className="font-mono text-caption text-primary" data-testid="dm-files">
          {data.manifestFile} + {data.lockFile}
        </p>
        <p className="font-mono text-caption text-on-surface-variant" data-testid="dm-python">
          requires-python {data.requiresPython}
        </p>
      </header>

      <div className="flex flex-col gap-xxs" data-testid="dm-groups">
        {data.groups.map((group) => (
          <p
            key={group.group}
            data-testid={`dm-group-${group.group}`}
            className="font-mono text-caption text-on-surface"
          >
            {group.group} — {group.directCount} direct, {group.declaredIn}
          </p>
        ))}
      </div>

      <div className="flex flex-col gap-xxs" data-testid="dm-direct">
        {main.map((row) => (
          <div
            key={row.name}
            data-testid={`dm-row-${row.name}`}
            className="flex flex-wrap items-baseline gap-x-sm font-mono text-caption"
          >
            <span className="text-on-surface">{row.name}</span>
            <span className="text-on-surface-variant">{row.constraint}</span>
            <span className="text-outline">→</span>
            <span className="text-primary">{row.lockedVersion}</span>
            <Verdict row={row} />
            {row.extras !== '' && (
              <span className="text-on-surface-variant">[{row.extras}]</span>
            )}
          </div>
        ))}
        {dev.length > 0 && (
          <p className="font-mono text-caption text-on-surface-variant" data-testid="dm-dev-names">
            dev · {dev.map((row) => row.name).join(', ')}
          </p>
        )}
      </div>

      {data.agreement !== null && (
        <p
          data-testid="dm-agreement"
          className={`font-mono text-caption ${
            data.agreement.agree ? 'text-primary' : 'text-error'
          }`}
        >
          manifest ↔ lock: {data.agreement.agree ? 'agree' : 'DRIFT'} ·{' '}
          {data.agreement.manifestNames} declared vs {data.agreement.lockNames} locked
          {data.agreement.missingFromLock.length > 0 &&
            ` · missing: ${data.agreement.missingFromLock.join(', ')}`}
        </p>
      )}

      {treeSlice !== null && (
        <section
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
          data-testid="dm-slice"
        >
          <p className="font-mono text-caption text-on-surface">
            <span className="text-primary">{treeSlice.root}</span>{' '}
            {treeSlice.rootConstraint} → {treeSlice.rootLockedVersion}
          </p>
          {treeSlice.children.map((child) => (
            <p key={child.name} className="font-mono text-caption text-on-surface-variant">
              ├─ {child.name} {child.lockedVersion}
            </p>
          ))}
          <p className="text-caption text-on-surface-variant" data-testid="dm-slice-note">
            {treeSlice.note}
          </p>
        </section>
      )}

      {data.counts !== null && (
        <p className="font-mono text-caption text-on-surface" data-testid="dm-counts">
          lock: {data.counts.totalLocked} total · {data.counts.direct} direct ·{' '}
          {data.counts.transitive} transitive
        </p>
      )}

      <p className="text-caption text-on-surface-variant" data-testid="dm-honesty-note">
        {data.honestyNote}
      </p>
    </section>
  );
}
