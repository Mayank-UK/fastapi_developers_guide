"""The gRPC adapters: the servicer, its in-process satellite, the console.

This package is topic 15's data layer. It hosts the whole gRPC satellite
because of ONE architectural fact: the ASGI app stays the front door, and
the gRPC server exists so the console's client calls are REAL end-to-end
(TCP on 127.0.0.1, protobuf frames, deadlines) — from the app's
perspective the satellite serves the outbound console, so adapter + host
live together here, importing the DOMAIN (posts use cases) and the
COMPILED CONTRACT (``guide.grpcapi``) and nothing else.

A standalone gRPC deployment would promote the servicer to its own
process (``grpc.aio.server`` in its own ``asyncio.run`` main, like
uvicorn for HTTP) — section 4 of the topic draws exactly that line.
"""
