/**
 * Domain models for the deployment topic's deploy-stack panel (demo block
 * id `deploy:stack`) — the client-side shape of GET /api/demo/deploy/stack.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The payload is one live inspection of the repo's deploy surface: the
 * runtime block carries facts THIS server process always has (env,
 * interpreter, pid, the server command line, a REAL internal /api/health),
 * and each area rows over one slice of the surface — the compose trio,
 * the edge, the images, the pipeline, the release, parity, kubernetes —
 * with verdicts that are only ever pass/fail/manual and evidence behind
 * every machine-judged one.
 */

/** One runtime fact about the serving process — always real, never manual. */
export interface RuntimeRow {
  id: string;
  label: string;
  value: string;
}

export type StackCheckKind = 'live' | 'file' | 'manual';

export type StackVerdict = 'pass' | 'fail' | 'manual';

/** One claim about the deploy surface, one verdict, the evidence. */
export interface StackItemRow {
  id: string;
  claim: string;
  checkKind: StackCheckKind;
  verdict: StackVerdict;
  evidence: string[];
  whyManual?: string;
}

/** One area of the deploy surface: its rows plus a one-line frame. */
export interface StackAreaRow {
  id: string;
  title: string;
  note: string;
  items: StackItemRow[];
}

/** Wire shape of GET /api/demo/deploy/stack — the panel's contract. */
export interface DeployStackPanel {
  runtime: RuntimeRow[];
  areas: StackAreaRow[];
  honestyNote: string;
}
