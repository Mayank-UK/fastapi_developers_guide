"""The gRPC area's domain vocabulary: console requests, call outcomes, the port.

Topic 15 mounts the posts substrate behind a gRPC contract
(``guide.grpcapi``, the compiled ``guide.proto``). This package owns the
DOMAIN half of that story — the shapes a console call speaks and the port
the data-layer adapter implements — while the servicer, the in-process
server, and the channel live in ``guide/data/grpc/`` and the compiled
contract lives in ``guide.grpcapi`` (both import-depend on the domain;
the dependency rule is untouched).
"""
