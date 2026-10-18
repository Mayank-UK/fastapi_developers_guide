/**
 * Domain models for the python-runtime topic's async-timing demo — the
 * client-side shape of `GET /api/demo/runtime/async`. Field names match the
 * server's camelCase wire contract 1:1 (the DTO is the seam where wire and
 * domain may diverge later). Every timing is measured server-side per
 * request; only the structure is stable.
 */

export interface IoTask {
  name: string;
  /** The simulated I/O delay this task was given, in milliseconds. */
  simulatedIoMs: number;
}

export interface TaskTiming extends IoTask {
  /** What the task's await actually cost, measured (>= simulatedIoMs). */
  measuredMs: number;
}

export interface TimingRun {
  strategy: 'sequential' | 'gathered';
  elapsedMs: number;
  /** Real finish order: start order when sequential, delay order when gathered. */
  completionOrder: string[];
  perTask: TaskTiming[];
}

export interface TraceEvent {
  actor: string;
  event: string;
}

export interface RuntimeAsyncDemoData {
  ioPlan: IoTask[];
  sequential: TimingRun;
  gathered: TimingRun;
  /** sequential.elapsedMs / gathered.elapsedMs — expected ~2, measured. */
  speedup: number;
  /** Two actors interleaving step by step: the await-yields-control proof. */
  trace: TraceEvent[];
}
