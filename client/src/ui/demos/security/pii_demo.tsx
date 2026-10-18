import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { MaskedSubject, PiiCredential, PiiPanel } from '../../../domain/demo/security-pii';
import { ErrorPanel } from '../../components/error-panel';

/**
 * PiiDemo — the security topic's PII lab (demo block id `security:pii`).
 * The panel carries the seeded subjects, the classification catalog, and
 * the role→mask-level table; the viewer select renders one subject AS THE
 * CHOSEN CALLER SEES IT (anonymous/viewer full mask, editor partial,
 * admin raw — the token is minted through the auth lab's use case).
 * Export and erase run with the SAME chosen credential, so the ladder is
 * the real one: anonymous meets the 401, a non-admin the 403 with its
 * reason, the admin succeeds. Reset reseeds the round.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: PiiPanel };

type Viewer = 'anonymous' | 'alan' | 'barbara' | 'ada';

const VIEWER_ROLES: Record<Viewer, string> = {
  anonymous: 'no credential',
  alan: 'viewer',
  barbara: 'editor',
  ada: 'admin',
};

type RoundStatus =
  | { state: 'idle' }
  | { state: 'failed'; failure: Failure }
  | { state: 'done'; message: string };

type MintedCredential = { ok: true; credential: PiiCredential } | { ok: false; failure: Failure };

export function PiiDemo() {
  const useCase = container.getSecurityPiiDemoUseCase;
  const mintUseCase = container.getAuthJwtDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [viewer, setViewer] = useState<Viewer>('anonymous');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [subject, setSubject] = useState<MaskedSubject | null>(null);
  const [round, setRound] = useState<RoundStatus>({ state: 'idle' });
  const [busy, setBusy] = useState(false);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      if (!result.ok) {
        setPanel({ state: 'failed', failure: result.failure });
        return;
      }
      setPanel({ state: 'ready', data: result.value });
      const roster = result.value.subjects;
      // Keep the current selection when it survived the refresh (an erase
      // followed by a reset changes the roster); else take the first row.
      setSelectedId((current) => {
        if (current !== null && roster.some((row) => row.customerId === current)) {
          return current;
        }
        return roster[0]?.customerId ?? null;
      });
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
  }, [refreshPanel]);

  const mintCredential = useCallback(
    async (chosen: Viewer): Promise<MintedCredential> => {
      if (chosen === 'anonymous') {
        return { ok: true, credential: null };
      }
      const minted = await mintUseCase.mint(chosen, ['*'], 900, 0, 'real');
      return minted.ok
        ? { ok: true, credential: { kind: 'bearer', token: minted.value.token } }
        : { ok: false, failure: minted.failure };
    },
    [mintUseCase],
  );

  const loadSubject = useCallback(
    (customerId: string, chosen: Viewer) => {
      setBusy(true);
      setRound({ state: 'idle' });
      void mintCredential(chosen).then((minted) => {
        if (!minted.ok) {
          setRound({ state: 'failed', failure: minted.failure });
          setBusy(false);
          return;
        }
        void useCase.subject(customerId, minted.credential).then((result) => {
          if (result.ok) {
            setSubject(result.value);
          } else {
            setSubject(null);
            setRound({ state: 'failed', failure: result.failure });
          }
          setBusy(false);
        });
      });
    },
    [mintCredential, useCase],
  );

  useEffect(() => {
    if (selectedId !== null) {
      loadSubject(selectedId, viewer);
    }
  }, [loadSubject, selectedId, viewer]);

  function runGated(kind: 'export' | 'erase'): void {
    if (selectedId === null) return;
    setBusy(true);
    void mintCredential(viewer).then((minted) => {
      if (!minted.ok) {
        setRound({ state: 'failed', failure: minted.failure });
        setBusy(false);
        return;
      }
      if (kind === 'export') {
        void useCase.exportSubject(selectedId, minted.credential).then((result) => {
          setRound(
            result.ok
              ? {
                  state: 'done',
                  message: `exported as ${result.value.principal}: ${result.value.record.email}`,
                }
              : { state: 'failed', failure: result.failure },
          );
          setBusy(false);
        });
        return;
      }
      void useCase.eraseSubject(selectedId, minted.credential).then((result) => {
        if (result.ok) {
          setRound({
            state: 'done',
            message: `erased: ${result.value.recordsBefore} → ${result.value.recordsAfter} records — the next read is the 404 envelope`,
          });
          setSubject(null);
          refreshPanel();
        } else {
          setRound({ state: 'failed', failure: result.failure });
        }
        setBusy(false);
      });
    });
  }

  function reset(): void {
    setBusy(true);
    void useCase.reset().then((result) => {
      setRound(
        result.ok
          ? { state: 'done', message: result.value.detail }
          : { state: 'failed', failure: result.failure },
      );
      setBusy(false);
      refreshPanel();
    });
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="security-pii-loading" className="text-body-sm text-on-surface-variant">
        reading the PII lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the PII lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="security-pii-classification"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        {data.classification.map((row) => (
          <p key={row.field} className="font-mono text-caption text-on-surface-variant">
            {row.field} · {row.category} · {row.tier}
            {row.allowsPartial ? ' · partial ok' : ' · full only'}
          </p>
        ))}
        {data.roleMasks.map((row) => (
          <p key={row.role} className="text-caption text-on-surface">
            <span className="font-mono text-primary">
              {row.role} → {row.maskLevel}
            </span>{' '}
            — {row.note}
          </p>
        ))}
        <p className="text-caption text-on-surface-variant">{data.minimizationNote}</p>
      </section>

      <section data-testid="security-pii-viewer" className="flex flex-wrap items-center gap-xs">
        <select
          value={viewer}
          onChange={(event) => setViewer(event.target.value as Viewer)}
          aria-label="viewer"
          className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
        >
          {(Object.keys(VIEWER_ROLES) as Viewer[]).map((name) => (
            <option key={name} value={name}>
              {name} ({VIEWER_ROLES[name]})
            </option>
          ))}
        </select>
        <select
          value={selectedId ?? ''}
          onChange={(event) => setSelectedId(event.target.value)}
          aria-label="subject"
          className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
        >
          {data.subjects.map((row) => (
            <option key={row.customerId} value={row.customerId}>
              {row.customerId} · {row.country}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={busy || selectedId === null}
          onClick={() => runGated('export')}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          export as {viewer}
        </button>
        <button
          type="button"
          disabled={busy || selectedId === null}
          onClick={() => runGated('erase')}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          erase as {viewer}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={reset}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          reset lab
        </button>
      </section>

      {subject && (
        <section
          data-testid="security-pii-subject"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            {subject.customerId} · {subject.principal} ({subject.principalRole ?? 'no role'}) ·
            mask {subject.maskLevel}
          </p>
          {subject.fields.map((field) => (
            <p key={field.field} className="font-mono text-caption text-on-surface-variant">
              {field.field} = {field.value}
              {field.masked ? ` (${field.applied})` : ''}
            </p>
          ))}
          <p className="text-caption text-on-surface-variant">{subject.detail}</p>
        </section>
      )}

      {round.state === 'done' && (
        <p data-testid="security-pii-round" className="font-mono text-caption text-primary">
          {round.message}
        </p>
      )}
      {round.state === 'failed' && (
        <p data-testid="security-pii-round-error" className="font-mono text-caption text-error">
          {round.failure.code}: {round.failure.message}
        </p>
      )}

      <p data-testid="security-pii-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning} ({data.storeCount} records in the store)
      </p>
    </div>
  );
}

export default PiiDemo;
