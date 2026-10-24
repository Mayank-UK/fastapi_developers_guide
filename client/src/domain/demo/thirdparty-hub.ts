/**
 * Domain models for the third-party topic's hub panel (demo block id
 * `thirdparty:hub`) — the client-side shape of
 * GET /api/demo/thirdparty/hub. Field names match the server's
 * camelCase wire contract 1:1.
 *
 * The panel is the topic's four inventories in one payload: the
 * integrate-vs-build walk (every row verified against the manifest or
 * the server tree on the very request that served it), the real
 * integration inventory with each dependency's honest failure mode,
 * the key/secret surface as names and blast radii — the server never
 * reads a secret value, so the wire cannot carry one — and the real
 * quotas, live where the process can read them.
 */

/** One integrate-vs-build decision this repo actually made. */
export interface DecisionRow {
  id: string;
  choice: 'integrate' | 'build';
  subject: string;
  package: string;
  reason: string;
  blastRadius: string;
  verified: string;
}

/** One real third-party integration: what it is, and what its failure does. */
export interface IntegrationRow {
  id: string;
  kind: string;
  name: string;
  detail: string;
  whenDown: string;
  evidence: string;
}

/** One key/secret in the real surface — named, scoped, blast-radius'd only. */
export interface SecretRow {
  id: string;
  envVar: string;
  scope: string;
  blastRadius: string;
  handling: string;
  evidence: string;
}

/** One real ceiling the app enforces — the number and the behavior at it. */
export interface QuotaRow {
  id: string;
  quota: string;
  scope: string;
  atCeiling: string;
  source: 'live' | 'constant';
}

/** Wire shape of GET /api/demo/thirdparty/hub — the panel's contract. */
export interface ThirdPartyHubPanel {
  decisions: DecisionRow[];
  integrations: IntegrationRow[];
  secrets: SecretRow[];
  quotas: QuotaRow[];
  honestyNote: string;
}
