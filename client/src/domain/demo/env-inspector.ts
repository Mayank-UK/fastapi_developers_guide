/**
 * Domain models for the environments topic's inspector (demo block id
 * `env:inspector`) — the client-side shape of GET /api/demo/env plus the
 * scenario store's PATCH answers. Field names match the server's camelCase
 * wire contract 1:1.
 *
 * The panel is one live read of the process's REAL configuration: every
 * setting with its env-var name, its type, the frozen instance's effective
 * value, and a source attribution derived from the same EnvSettingsSource
 * pydantic-settings consults — 'env' when the process environment provides
 * the field, 'default' when it fell back. Secret-bearing rows arrive
 * already redacted server-side: the value is the word "redacted" and only
 * a length hint survives.
 */

/** Where a setting's value came from: the environment, or the declared default. */
export type SettingSource = 'env' | 'default';

/** The scenario store's flag vocabulary (the repo's real runtime flags). */
export type DataMode = 'fake' | 'live';
export type FailureInjection = 'none' | 'error' | 'latency';

/** One config field row: env-var name, type, value, source, redaction state. */
export interface SettingRow {
  name: string;
  envVar: string;
  type: string;
  value: string;
  source: SettingSource;
  secret: boolean;
  redacted: boolean;
  shapeHint: string | null;
}

/** The config's own mechanics, read off the class — not restated. */
export interface ConfigFactsRow {
  envPrefix: string;
  frozen: boolean;
  cache: string;
}

/** The flags sub-panel: the live snapshot plus the real endpoints. */
export interface FlagsPanelRow {
  getEndpoint: string;
  patchEndpoint: string;
  dataMode: DataMode;
  injectFailure: FailureInjection;
  note: string;
}

/** Wire shape of GET /api/demo/env — the inspector panel's contract. */
export interface EnvInspectorPanel {
  environment: string;
  envVar: string;
  facts: ConfigFactsRow;
  settings: SettingRow[];
  sourceNote: string;
  redactionNote: string;
  flags: FlagsPanelRow;
}

/** The scenario store's answer after a PATCH (its current snapshot). */
export interface ScenarioSnapshot {
  dataMode: DataMode;
  injectFailure: FailureInjection;
}
