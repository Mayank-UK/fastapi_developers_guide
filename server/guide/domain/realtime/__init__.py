"""Topic 28's realtime substrate: SSE framing, the ticker, and chat rooms.

Three real engines live here — none is a teaching exhibit. ``frames`` owns
the ``text/event-stream`` wire format as pure functions; ``log`` owns the
bounded seq-keyed rings both directions of resumption read from; ``ticker``
mints the simulated market's events (deterministic prices, injected clock
and sleeper); ``manager`` + ``chat`` own the websocket side — rooms,
fanout over per-connection queues with a ceiling, and the chat protocol.
"""
