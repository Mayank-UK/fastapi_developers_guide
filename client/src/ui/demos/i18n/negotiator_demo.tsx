import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { I18nPanel, NegotiatorRound } from '../../../domain/demo/i18n-negotiator';
import { ErrorPanel } from '../../components/error-panel';

/**
 * NegotiatorDemo — the i18n topic's lab (demo block id `i18n:negotiator`).
 * One header in, one fully-changed world out: presets and free text set
 * the Accept-Language the round actually sends (or omit it, and the
 * browser's own rides), and the answer shows the whole ranked parse —
 * then everything the negotiated locale moves: catalog-served UI strings,
 * CLDR number/currency/date formatting, plural categories with their
 * real sentences, and the fixed instant on three wall clocks labeled in
 * that locale.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: I18nPanel };

/** A preset the panel can send: a label and the header value (null = omit). */
interface HeaderPreset {
  label: string;
  value: string | null;
}

const PRESETS: HeaderPreset[] = [
  { label: 'no header (browser default)', value: null },
  { label: 'de-DE,de;q=0.9,en;q=0.5', value: 'de-DE,de;q=0.9,en;q=0.5' },
  { label: 'pl-PL,pl;q=0.8,en;q=0.3', value: 'pl-PL,pl;q=0.8,en;q=0.3' },
  { label: 'fr-CA,fr;q=0.9 (unknown)', value: 'fr-CA,fr;q=0.9' },
  { label: '* (wildcard)', value: '*' },
  { label: 'en;q=0, * (exclusion)', value: 'en;q=0, *' },
  { label: 'garbage + junk q', value: '!!!, 1nvalid, de;q=2, pl;q=abc' },
];

const buttonClass =
  'w-fit rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50';
const fieldClass =
  'rounded-md border border-outline bg-surface-tint px-sm py-xxs font-mono text-caption text-on-surface';

function failureText(failure: Failure): string {
  return `${failure.code}: ${failure.message}`;
}

export function NegotiatorDemo() {
  const useCase = container.getI18nNegotiatorDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [headerInput, setHeaderInput] = useState('de-DE,de;q=0.9,en;q=0.5');
  const [round, setRound] = useState<NegotiatorRound | null>(null);
  const [roundFailure, setRoundFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      if (result.ok) {
        setPanel({ state: 'ready', data: result.value });
      } else {
        setPanel({ state: 'failed', failure: result.failure });
      }
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
  }, [refreshPanel]);

  function negotiate(value: string | null): void {
    setBusy(true);
    setRoundFailure(null);
    void useCase.negotiate(value).then((result) => {
      if (result.ok) {
        setRound(result.value);
      } else {
        setRound(null);
        setRoundFailure(failureText(result.failure));
      }
      setBusy(false);
    });
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="i18n-negotiator-loading" className="text-body-sm text-on-surface-variant">
        opening the i18n negotiator…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the i18n negotiator" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { policy } = panel.data;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="i18n-negotiator-policy" className="flex flex-col gap-xxs">
        <p className="font-mono text-caption text-on-surface">
          default {policy.defaultLocale} · servable{' '}
          {policy.supportedLocales
            .map((locale) => `${locale.tag} (${locale.nativeName})`)
            .join(' · ')}{' '}
          · fixed instant {policy.fixedInstant}
        </p>
        {panel.data.honestyNotes.map((note) => (
          <p key={note} className="text-caption text-on-surface-variant">
            · {note}
          </p>
        ))}
      </section>

      <section data-testid="i18n-negotiator-controls" className="flex flex-col gap-xs">
        <div className="flex flex-wrap gap-xs">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className={buttonClass}
              disabled={busy}
              onClick={() => negotiate(preset.value)}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-xs">
          <input
            className={`${fieldClass} min-w-64 flex-1`}
            value={headerInput}
            onChange={(event) => setHeaderInput(event.target.value)}
            placeholder="type any Accept-Language value"
            aria-label="accept-language value"
          />
          <button
            type="button"
            className={buttonClass}
            disabled={busy || headerInput.trim().length === 0}
            onClick={() => negotiate(headerInput.trim())}
          >
            send this header
          </button>
        </div>
      </section>

      {roundFailure && (
        <p role="alert" className="text-caption text-error">
          {roundFailure}
        </p>
      )}

      {round && (
        <section data-testid="i18n-negotiator-round" className="flex flex-col gap-sm">
          <p data-testid="i18n-negotiator-verdict" className="font-mono text-caption text-on-surface">
            header {round.header ?? '(absent)'} → locale {round.selectedLocale} · via{' '}
            {round.matchedVia}
            {round.fellBackToDefault ? ' · fell back to default' : ''}
          </p>

          <div data-testid="i18n-negotiator-ranges" className="flex flex-col gap-xxs">
            <p className="text-caption text-on-surface-variant">the ranked parse:</p>
            {round.ranges.length === 0 && (
              <p className="font-mono text-caption text-on-surface-variant">
                (no valid elements — the default answered)
              </p>
            )}
            {round.ranges.map((range) => (
              <p key={`${range.raw}-${range.tag}`} className="font-mono text-caption text-on-surface">
                {range.raw} · tag {range.tag} · q {range.quality} · {range.matchedVia}
                {range.matchedLocale ? ` → ${range.matchedLocale}` : ''}
              </p>
            ))}
          </div>

          <div data-testid="i18n-negotiator-strings" className="flex flex-col gap-xxs">
            <p className="text-caption text-on-surface-variant">
              UI strings, served from the real catalog:
            </p>
            {round.uiStrings.map((string) => (
              <p key={string.msgid} className="text-caption text-on-surface">
                {string.value}
                <span className="text-on-surface-variant"> — {string.msgid}</span>
              </p>
            ))}
          </div>

          <p data-testid="i18n-negotiator-formatting" className="font-mono text-caption text-on-surface">
            {round.formatting.numberInput} → {round.formatting.number} ·{' '}
            {round.formatting.currencyAmount} {round.formatting.currencyCode} →{' '}
            {round.formatting.currency} · {round.formatting.instant} → {round.formatting.date}
          </p>

          <div data-testid="i18n-negotiator-plurals" className="flex flex-col gap-xxs">
            <p className="text-caption text-on-surface-variant">
              plural categories (CLDR) with the served sentence:
            </p>
            {round.plurals.map((plural) => (
              <p key={plural.count} className="font-mono text-caption text-on-surface">
                {plural.count} → {plural.category} · {plural.sentence}
              </p>
            ))}
          </div>

          <div data-testid="i18n-negotiator-zones" className="flex flex-col gap-xxs">
            <p className="text-caption text-on-surface-variant">
              the same instant on three walls, labeled in {round.selectedLocale}:
            </p>
            {round.zones.map((zone) => (
              <p key={zone.zone} className="font-mono text-caption text-on-surface">
                {zone.zone} · {zone.wallTime} · {zone.utcOffset} {zone.abbreviation} ·{' '}
                {zone.formatted}
              </p>
            ))}
          </div>
        </section>
      )}

      <section data-testid="i18n-negotiator-catalog" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">the catalogs, as they stand:</p>
        {panel.data.catalog.map((row) => (
          <p key={row.msgid} className="text-caption text-on-surface">
            {row.translations
              .map(
                (cell) =>
                  `${cell.locale}: ${cell.served}${cell.translated ? '' : ' (fallback)'}`,
              )
              .join(' · ')}
            <span className="text-on-surface-variant"> — {row.msgid}</span>
          </p>
        ))}
      </section>
    </div>
  );
}

export default NegotiatorDemo;
