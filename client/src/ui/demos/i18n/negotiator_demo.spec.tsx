import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { NegotiatorDemo } from './negotiator_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetI18nNegotiatorDemoUseCase } from '../../../domain/demo/get-i18n-negotiator-demo-usecase';
import type { I18nPanel, NegotiatorRound } from '../../../domain/demo/i18n-negotiator';

/**
 * NegotiatorDemo spec — fixture-driven (happy + failure): the panel renders
 * the policy (servable locales, fixed instant) and the catalog state; a
 * preset sends its Accept-Language and the round renders the ranked parse,
 * the negotiated verdict, strings, formatting, plurals, and zones; a Failed
 * panel degrades to the shared error panel with recovery.
 */

const panel: I18nPanel = {
  policy: {
    defaultLocale: 'en',
    supportedLocales: [
      { tag: 'en', englishName: 'English', nativeName: 'English', pluralCategories: ['one', 'other'] },
      { tag: 'de', englishName: 'German', nativeName: 'Deutsch', pluralCategories: ['one', 'other'] },
      { tag: 'pl', englishName: 'Polish', nativeName: 'polski', pluralCategories: ['one', 'few', 'many', 'other'] },
    ],
    fixedInstant: '2026-03-08T07:30:00+00:00',
    numberInput: 1234567.89,
    currencyCode: 'EUR',
    currencyAmount: 1234.5,
    pluralCounts: [0, 1, 2, 5, 22],
  },
  catalog: [
    {
      msgid: 'Upload a file',
      translations: [
        { locale: 'de', served: 'Datei hochladen', translated: true },
        { locale: 'pl', served: 'Wyślij plik', translated: true },
      ],
    },
    {
      msgid: 'Language',
      translations: [
        { locale: 'de', served: 'Language', translated: false },
        { locale: 'pl', served: 'Język', translated: true },
      ],
    },
  ],
  endpoints: [
    {
      path: '/api/demo/i18n/negotiate',
      method: 'GET',
      teaches: 'send any Accept-Language',
    },
  ],
  honestyNotes: ['hand-written demo-scope .po catalogs'],
  reasoning: 'Negotiate, then serve every layer in the negotiated locale.',
};

const germanRound: NegotiatorRound = {
  header: 'de-DE,de;q=0.9,en;q=0.5',
  selectedLocale: 'de',
  matchedVia: 'region-fallback',
  fellBackToDefault: false,
  ranges: [
    { raw: 'de-DE', tag: 'de-de', quality: 1, matchedLocale: 'de', matchedVia: 'region-fallback' },
    { raw: 'de', tag: 'de', quality: 0.9, matchedLocale: 'de', matchedVia: 'exact' },
    { raw: 'en', tag: 'en', quality: 0.5, matchedLocale: 'en', matchedVia: 'exact' },
  ],
  uiStrings: [
    { msgid: 'Upload a file', value: 'Datei hochladen' },
    { msgid: 'Language', value: 'Language' },
  ],
  formatting: {
    numberInput: 1234567.89,
    number: '1.234.567,89',
    currencyCode: 'EUR',
    currencyAmount: 1234.5,
    currency: '1.234,50 €',
    instant: '2026-03-08T07:30:00+00:00',
    date: '08.03.2026, 07:30:00',
  },
  plurals: [
    { count: 0, category: 'other', sentence: '0 Dateien wurden hochgeladen' },
    { count: 1, category: 'one', sentence: '1 Datei wurde hochgeladen' },
    { count: 2, category: 'other', sentence: '2 Dateien wurden hochgeladen' },
  ],
  zones: [
    { zone: 'UTC', wallTime: '2026-03-08T07:30:00+00:00', utcOffset: '+00:00', abbreviation: 'UTC', formatted: '08.03.2026, 07:30:00' },
    { zone: 'America/New_York', wallTime: '2026-03-08T03:30:00-04:00', utcOffset: '-04:00', abbreviation: 'EDT', formatted: '08.03.2026, 03:30:00' },
  ],
};

const polishRound: NegotiatorRound = {
  ...germanRound,
  header: 'pl',
  selectedLocale: 'pl',
  matchedVia: 'exact',
  plurals: [
    { count: 0, category: 'many', sentence: '0 plików zostało wysłanych' },
    { count: 1, category: 'one', sentence: '1 plik został wysłany' },
    { count: 2, category: 'few', sentence: '2 pliki zostały wysłane' },
    { count: 5, category: 'many', sentence: '5 plików zostało wysłanych' },
    { count: 22, category: 'few', sentence: '22 pliki zostały wysłane' },
  ],
};

type Stubs = {
  panel?: () => Promise<Result<I18nPanel>>;
  negotiate?: (acceptLanguage: string | null) => Promise<Result<NegotiatorRound>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetI18nNegotiatorDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    negotiate:
      stubs.negotiate ??
      (async (acceptLanguage: string | null) =>
        success(acceptLanguage === 'pl' ? polishRound : germanRound)),
  } as unknown as GetI18nNegotiatorDemoUseCase);
}

describe('NegotiatorDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['i18n:negotiator']).toBeDefined();
  });

  it('renders the policy and the catalog state', async () => {
    stubUseCase({});
    render(<NegotiatorDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-policy')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('i18n-negotiator-policy')).toHaveTextContent(
      'default en',
    );
    expect(screen.getByTestId('i18n-negotiator-policy')).toHaveTextContent(
      'Deutsch',
    );
    expect(screen.getByTestId('i18n-negotiator-catalog')).toHaveTextContent(
      'Language (fallback)',
    );
  });

  it('sends a preset header and renders the full round', async () => {
    let sent: string | null = 'unset';
    stubUseCase({
      negotiate: async (acceptLanguage) => {
        sent = acceptLanguage;
        return success(germanRound);
      },
    });
    render(<NegotiatorDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-policy')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'de-DE,de;q=0.9,en;q=0.5' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-round')).toBeInTheDocument(),
    );
    expect(sent).toBe('de-DE,de;q=0.9,en;q=0.5');
    expect(screen.getByTestId('i18n-negotiator-verdict')).toHaveTextContent(
      'locale de · via region-fallback',
    );
    expect(screen.getByTestId('i18n-negotiator-ranges')).toHaveTextContent(
      'de-DE · tag de-de · q 1 · region-fallback → de',
    );
    expect(screen.getByTestId('i18n-negotiator-strings')).toHaveTextContent(
      'Datei hochladen — Upload a file',
    );
    expect(screen.getByTestId('i18n-negotiator-formatting')).toHaveTextContent(
      '1.234.567,89',
    );
    expect(screen.getByTestId('i18n-negotiator-zones')).toHaveTextContent(
      'America/New_York · 2026-03-08T03:30:00-04:00 · -04:00 EDT',
    );
  });

  it('renders the absent-header preset as a normal round', async () => {
    let sent: string | null = 'unset';
    stubUseCase({
      negotiate: async (acceptLanguage) => {
        sent = acceptLanguage;
        return success({ ...germanRound, header: null, fellBackToDefault: true, ranges: [] });
      },
    });
    render(<NegotiatorDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-policy')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'no header (browser default)' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-round')).toBeInTheDocument(),
    );
    expect(sent).toBeNull();
    expect(screen.getByTestId('i18n-negotiator-verdict')).toHaveTextContent(
      'header (absent)',
    );
    expect(screen.getByTestId('i18n-negotiator-ranges')).toHaveTextContent(
      'no valid elements',
    );
  });

  it('shows the polish plural category math', async () => {
    stubUseCase({});
    render(<NegotiatorDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-policy')).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByLabelText('accept-language value'), {
      target: { value: 'pl' },
    });

    screen.getByRole('button', { name: 'send this header' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-round')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('i18n-negotiator-plurals')).toHaveTextContent(
      '22 → few · 22 pliki zostały wysłane',
    );
    expect(screen.getByTestId('i18n-negotiator-plurals')).toHaveTextContent(
      '5 → many · 5 plików zostało wysłanych',
    );
  });

  it('degrades to the shared error panel on a Failed panel, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      panel: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Could not reach the server.', {
                code: 'unknown_error',
                status: 0,
                requestId: 'req-h1',
              }),
            )
          : success(panel);
      },
    });
    render(<NegotiatorDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('i18n-negotiator-policy')).toBeInTheDocument(),
    );
  });
});
