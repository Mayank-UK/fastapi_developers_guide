import { useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  SignedDelivery,
  WebhookEventType,
  WebhookReceipt,
  WebhookScenario,
  WebhookSimulation,
  WebhookSimulatorRoster,
} from '../../../domain/demo/webhook-simulator';

/**
 * WebhookSimulatorDemo — the webhooks topic's console (demo block id
 * `api:webhook-simulator`). Loads the roster (scenarios, the event
 * catalog, the public teaching secret, the exact attempt schedule),
 * then registers a subscription and fires an event at the chosen target
 * scenario: the result walks every simulated delivery attempt — offset,
 * signing timestamp, real HMAC signature, answered status — and lands on
 * the verdict, with the dead-letter entry when the budget ran out.
 *
 * The deliverByHand section crosses into §5 for real: the same signed
 * round fires at the LIVE receive endpoint, once honestly (a 202
 * receipt) and once with one tampered body byte (the 401 envelope —
 * rendered inline with its code and status, because a refused forgery
 * is the receiver doing its job, not a broken screen). Transport
 * failures degrade to the shared ErrorPanel with recovery.
 */

type RosterStatus =
  | { state: 'loading' }
  | { state: 'ready'; roster: WebhookSimulatorRoster }
  | { state: 'failed'; failure: Failure };

type SimulationStatus =
  | { state: 'idle' }
  | { state: 'busy' }
  | { state: 'done'; simulation: WebhookSimulation }
  | { state: 'failed'; failure: Failure };

type DeliverStatus =
  | { state: 'idle' }
  | { state: 'busy'; kind: 'signed' | 'tampered' }
  | { state: 'accepted'; receipt: WebhookReceipt; kind: 'signed' | 'tampered' }
  | { state: 'refused'; failure: Failure; kind: 'tampered' }
  | { state: 'failed'; failure: Failure; kind: 'signed' | 'tampered' };

const inputClass =
  'rounded-md border border-outline bg-surface-tint px-sm py-xxs font-mono ' +
  'text-caption text-on-surface focus:border-primary focus:outline-none';

const chipClass = (active: boolean): string =>
  active
    ? 'rounded-pill border border-primary bg-surface-tint px-sm py-xxs font-mono text-caption text-primary'
    : 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption ' +
      'text-on-surface-variant transition-colors hover:border-primary hover:text-primary';

const actionClass =
  'self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption ' +
  'uppercase tracking-wide text-on-surface transition-colors hover:border-primary ' +
  'hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

const verdictClass = (delivered: boolean): string =>
  delivered
    ? 'rounded-md border border-outline px-sm py-xs font-mono text-caption text-on-surface'
    : 'rounded-md border border-error px-sm py-xs font-mono text-caption text-on-surface';

function DeliverOutcome({ status }: { status: DeliverStatus }) {
  if (status.state === 'busy') {
    return (
      <p data-testid="ws-deliver-busy" className="text-caption text-on-surface-variant">
        POSTing the round at the live receive endpoint…
      </p>
    );
  }
  if (status.state === 'accepted') {
    return (
      <div
        data-testid="ws-deliver-accepted"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          <span className="text-secondary">202 Accepted</span> — eventId:{' '}
          {status.receipt.eventId ?? '(unparseable body)'} · age {String(status.receipt.ageSeconds)}s
        </p>
        <p className="text-caption text-on-surface-variant">{status.receipt.detail}</p>
      </div>
    );
  }
  if (status.state === 'refused') {
    return (
      <div
        data-testid="ws-deliver-refused"
        className="flex flex-col gap-xxs rounded-md border border-error px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          <span className="text-error">{String(status.failure.status)} {status.failure.code}</span>
          {' '}— the receiver refused the tampered bytes
        </p>
        <p className="text-caption text-on-surface-variant">{status.failure.message}</p>
      </div>
    );
  }
  if (status.state === 'failed') {
    return (
      <div data-testid="ws-deliver-failed" className="rounded-md border border-outline px-sm py-xs">
        <p className="font-mono text-caption text-on-surface">
          <span className="text-error">{String(status.failure.status)} {status.failure.code}</span>
        </p>
        <p className="text-caption text-on-surface-variant">{status.failure.message}</p>
      </div>
    );
  }
  return null;
}

export function WebhookSimulatorDemo() {
  const useCase = container.getWebhookSimulatorDemoUseCase;
  const [roster, setRoster] = useState<RosterStatus>({ state: 'loading' });
  const [scenario, setScenario] = useState<WebhookScenario>('flaky-then-success');
  const [eventType, setEventType] = useState<WebhookEventType>('post.published');
  const [note, setNote] = useState('');
  const [simulation, setSimulation] = useState<SimulationStatus>({ state: 'idle' });
  const [deliver, setDeliver] = useState<DeliverStatus>({ state: 'idle' });
  const loadedOnce = useRef(false);

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    // Mount-once: the roster loads the moment the demo renders; the use
    // case is container-resolved so specs swap the token.
    void useCase.roster().then((result) => {
      setRoster(
        result.ok
          ? { state: 'ready', roster: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, []);

  const retryRoster = () => {
    setRoster({ state: 'loading' });
    void useCase.roster().then((result) => {
      setRoster(
        result.ok
          ? { state: 'ready', roster: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  const fire = () => {
    setSimulation({ state: 'busy' });
    setDeliver({ state: 'idle' });
    void useCase
      .simulate({
        eventType,
        scenario,
        ...(note.trim() === '' ? {} : { note: note.trim() }),
      })
      .then((result) => {
        setSimulation(
          result.ok
            ? { state: 'done', simulation: result.value }
            : { state: 'failed', failure: result.failure },
        );
      });
  };

  const deliverRound = (kind: 'signed' | 'tampered') => {
    if (simulation.state !== 'done') return;
    const signed: SignedDelivery = simulation.simulation.deliverByHand;
    setDeliver({ state: 'busy', kind });
    const round = kind === 'signed' ? useCase.deliver(signed) : useCase.deliverTampered(signed);
    void round.then((result) => {
      if (result.ok) {
        setDeliver({ state: 'accepted', receipt: result.value, kind });
        return;
      }
      // A 401 unauthorized from the TAMPERED round is the expected lesson —
      // render it inline; anything else is a transport failure.
      if (kind === 'tampered' && result.failure.code === 'unauthorized') {
        setDeliver({ state: 'refused', failure: result.failure, kind });
        return;
      }
      setDeliver({ state: 'failed', failure: result.failure, kind });
    });
  };

  if (roster.state === 'loading') {
    return (
      <p data-testid="ws-loading" className="text-body-sm text-on-surface-variant">
        reading the roster — scenarios, secret, schedule…
      </p>
    );
  }

  if (roster.state === 'failed') {
    return <ErrorPanel subject="the webhook simulator" failure={roster.failure} onRetry={retryRoster} />;
  }

  const { roster: loaded } = roster;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="ws-roster" className="flex flex-col gap-sm">
        <p data-testid="ws-facts" className="font-mono text-caption text-on-surface">
          <span className="text-secondary">secret</span> {loaded.secret}
          <span className="text-on-surface-variant">
            {' '}· {String(loaded.policy.maxAttempts)} attempts at offsets{' '}
            {loaded.policy.offsets.map((offset) => `+${String(offset)}s`).join(' ')}
          </span>
        </p>

        <div className="flex flex-wrap items-center gap-xxs">
          <span className="text-caption text-on-surface-variant">target scenario:</span>
          {loaded.scenarios.map((card) => (
            <button
              key={card.id}
              type="button"
              data-testid="ws-scenario"
              title={card.description}
              onClick={() => setScenario(card.id)}
              className={chipClass(card.id === scenario)}
            >
              {card.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-sm">
          <label className="flex items-center gap-xxs">
            <span className="text-caption text-on-surface-variant">event</span>
            <select
              data-testid="ws-event-type"
              className={inputClass}
              value={eventType}
              onChange={(event) => setEventType(event.target.value as WebhookEventType)}
            >
              {loaded.eventTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-xxs">
            <span className="text-caption text-on-surface-variant">note</span>
            <input
              data-testid="ws-note"
              className={inputClass}
              value={note}
              maxLength={200}
              placeholder="rides inside the event body"
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <button
            type="button"
            data-testid="ws-fire"
            onClick={fire}
            disabled={simulation.state === 'busy'}
            className={actionClass}
          >
            Fire the event
          </button>
        </div>

        <p data-testid="ws-reasoning" className="text-body-sm text-on-surface-variant">
          {loaded.reasoning}
        </p>
      </section>

      {simulation.state === 'failed' && (
        <ErrorPanel
          subject="the simulation"
          failure={simulation.failure}
          onRetry={fire}
        />
      )}

      {simulation.state === 'busy' && (
        <p data-testid="ws-busy" className="text-body-sm text-on-surface-variant">
          walking the delivery lifecycle…
        </p>
      )}

      {simulation.state === 'done' && <SimulationResult simulation={simulation.simulation} />}

      {simulation.state === 'done' && (
        <section data-testid="ws-deliver" className="flex flex-col gap-sm">
          <p className="text-caption text-on-surface-variant">
            deliverByHand is a genuinely fireable signed round — send it at the live
            receive endpoint, honestly or with one tampered body byte:
          </p>
          <div className="flex flex-wrap items-center gap-sm">
            <button
              type="button"
              data-testid="ws-deliver-signed"
              onClick={() => deliverRound('signed')}
              disabled={deliver.state === 'busy'}
              className={actionClass}
            >
              Deliver signed (expect 202)
            </button>
            <button
              type="button"
              data-testid="ws-deliver-tampered"
              onClick={() => deliverRound('tampered')}
              disabled={deliver.state === 'busy'}
              className={actionClass}
            >
              Deliver tampered (expect 401)
            </button>
          </div>
          <DeliverOutcome status={deliver} />
        </section>
      )}
    </div>
  );
}

function SimulationResult({ simulation }: { simulation: WebhookSimulation }) {
  const delivered = simulation.verdict === 'delivered';
  return (
    <section data-testid="ws-result" className="flex flex-col gap-sm">
      <p data-testid="ws-verdict" className={verdictClass(delivered)}>
        <span className={delivered ? 'text-secondary' : 'text-error'}>
          {simulation.verdict}
        </span>
        {delivered && simulation.deliveredAtOffset !== undefined
          ? ` on attempt ${String(simulation.attempts.length)} at +${String(simulation.deliveredAtOffset)}s`
          : ` after ${String(simulation.attempts.length)} attempt(s)`}
        <span className="text-on-surface-variant">
          {' '}· {simulation.subscription.id} → {simulation.subscription.url}
        </span>
      </p>

      <div data-testid="ws-attempts" className="flex flex-col gap-xxs">
        {simulation.attempts.map((attempt) => (
          <p key={attempt.attempt} data-testid="ws-attempt" className="font-mono text-caption text-on-surface">
            <span className="text-on-surface-variant">
              #{String(attempt.attempt)} +{String(attempt.offsetSeconds)}s
            </span>{' '}
            ts={String(attempt.timestamp)} sig={attempt.signature.slice(0, 23)}…{' '}
            <span className={attempt.status === 200 ? 'text-secondary' : 'text-error'}>
              {String(attempt.status)} ({attempt.outcome})
            </span>
          </p>
        ))}
      </div>

      {simulation.deadLetter !== undefined && (
        <div
          data-testid="ws-dead-letter"
          className="flex flex-col gap-xxs rounded-md border border-error px-sm py-xs"
        >
          <p className="font-mono text-caption text-on-surface">
            dead-letter · {simulation.deadLetter.eventId} · {String(simulation.deadLetter.attempts)}{' '}
            attempts · last {String(simulation.deadLetter.lastStatus)} at{' '}
            +{String(simulation.deadLetter.finalOffsetSeconds)}s
          </p>
          <p className="text-caption text-on-surface-variant">{simulation.deadLetter.reason}</p>
        </div>
      )}

      <p data-testid="ws-simulation-reasoning" className="text-body-sm text-on-surface-variant">
        {simulation.reasoning}
      </p>
    </section>
  );
}

export default WebhookSimulatorDemo;
