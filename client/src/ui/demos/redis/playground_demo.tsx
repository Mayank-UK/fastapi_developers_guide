import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  RedisPlaygroundDemo as RedisPlaygroundModel,
  StructureRow,
} from '../../../domain/demo/redis-playground';

/**
 * RedisPlaygroundDemo — the redis topic's playground (demo block id
 * `redis:playground`). One payload carries the whole scripted walk
 * against the live Redis: the five core structures with their real
 * commands and read-backs (string with the atomic INCR counter, hash,
 * list with its push-order inversion, set, sorted set in score order),
 * the honest TTL expiry proof (the live clock, then the key's absence
 * after the bounded wait), and a real pub/sub round-trip reported from
 * both sides. Pick a different tag to walk a fresh key family.
 */

type PlaygroundStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: RedisPlaygroundModel }
  | { state: 'failed'; failure: Failure };

const TAGS = ['demo', 'tour', 'second-run'];

export function RedisPlaygroundDemo() {
  const useCase = container.getRedisPlaygroundDemoUseCase;
  const [tag, setTag] = useState('demo');
  const [status, setStatus] = useState<PlaygroundStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.run(tag).then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase, tag]);

  const runAgain = () => {
    setStatus({ state: 'loading' });
    void useCase.run(tag).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="redis-playground-loading" className="text-body-sm text-on-surface-variant">
        walking the structures… (the TTL proof waits out a real 2 s expiry)
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the redis playground" failure={status.failure} onRetry={runAgain} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <div data-testid="redis-playground-tag-picker" className="flex flex-wrap items-center gap-xs">
        <span className="text-caption text-on-surface-variant">key family tag:</span>
        {TAGS.map((candidate) => (
          <button
            key={candidate}
            type="button"
            onClick={() => setTag(candidate)}
            className={`rounded-md border px-xs py-xxs font-mono text-caption ${
              candidate === tag
                ? 'border-primary text-primary'
                : 'border-outline text-on-surface-variant hover:text-on-surface'
            }`}
          >
            {candidate}
          </button>
        ))}
      </div>

      {data.structures.map((structure) => (
        <StructureRun key={structure.kind} structure={structure} />
      ))}

      <section
        data-testid="redis-playground-ttl"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          ttl proof · {data.ttl.key}
        </p>
        <p data-testid="redis-playground-ttl-proof" className="font-mono text-caption text-on-surface">
          configured {data.ttl.ttlSeconds}s · clock read {data.ttl.ttlFirstRead}s · waited{' '}
          {data.ttl.waitedMs}ms · absent after expiry:{' '}
          <span className={data.ttl.absentAfterExpiry ? 'text-primary' : 'text-error'}>
            {String(data.ttl.absentAfterExpiry)}
          </span>
        </p>
        {data.ttl.commands.map((command) => (
          <p key={command} className="font-mono text-caption text-on-surface-variant">
            {command}
          </p>
        ))}
        <p className="text-caption text-on-surface-variant">{data.ttl.proof}</p>
      </section>

      <section
        data-testid="redis-playground-pubsub"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">pub/sub proof · {data.pubsub.channel}</p>
        <p data-testid="redis-playground-pubsub-proof" className="font-mono text-caption text-on-surface">
          publish answered {data.pubsub.receivers} receiver(s) · listener matched:{' '}
          <span className={data.pubsub.matched ? 'text-primary' : 'text-error'}>
            {String(data.pubsub.matched)}
          </span>
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          payload: {data.pubsub.payload}
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          received: {data.pubsub.receivedPayload}
        </p>
        <p className="text-caption text-on-surface-variant">{data.pubsub.proof}</p>
      </section>

      <p data-testid="redis-playground-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function StructureRun({ structure }: { structure: StructureRow }) {
  return (
    <section
      data-testid={`redis-playground-${structure.kind}`}
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="font-mono text-caption text-on-surface">
        <span className="text-secondary">{structure.kind}</span> — {structure.key}
      </p>
      {structure.commands.map((command) => (
        <p key={command} className="font-mono text-caption text-on-surface-variant">
          {command}
        </p>
      ))}
      {structure.values.map((row, index) => (
        <p key={index} className="font-mono text-caption text-on-surface-variant">
          {row.label} = {row.value}
        </p>
      ))}
      <p className="font-mono text-caption text-on-surface">{structure.outcome}</p>
      <p className="text-caption text-on-surface-variant">{structure.description}</p>
    </section>
  );
}

export default RedisPlaygroundDemo;
