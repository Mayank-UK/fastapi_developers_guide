"""The compiled gRPC contract: generated code + the .proto it came from.

``guide.proto`` in this directory is the PostService contract (topic 15);
``guide_pb2.py`` and ``guide_pb2_grpc.py`` are ITS COMPILED FORM, produced
by ``grpc_tools.protoc`` and committed so no deploy needs the compiler.
Regenerate after editing the .proto (from ``server/``)::

    uv run python -m grpc_tools.protoc -I. \\
        --python_out=. --grpc_python_out=. guide/grpcapi/guide.proto

The generated modules are deliberately exempt from the ruff/mypy gates
(pyproject: per-file-ignores + mypy exclude) — they are build output, and
every hand-written module around them stays fully gated. Import the
messages and servicer base through this package::

    from guide.grpcapi import guide_pb2, guide_pb2_grpc
"""
