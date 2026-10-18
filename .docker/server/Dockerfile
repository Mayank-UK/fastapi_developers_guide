# Dev server image: uv sync bakes .venv into the image layer; compose then
# bind-mounts live source over /app and shadows .venv with an anonymous
# volume seeded from this layer — so deps survive every boot while code
# edits land hot (--reload). Build context: repo root.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

# Manifests first to leverage Docker layer caching (deps change least).
# --no-install-project: the guide source is not here yet; installing the
# project in this layer would fail (nothing to build from).
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --locked --no-install-project

COPY server/ ./
# Second sync adds the guide package itself — editable, so the venv points at
# /app and compose's bind-mounted live source is what runs under --reload.
RUN uv sync --locked

EXPOSE 8000
# The venv binary directly (not `uv run`): no implicit sync at boot — the
# anonymous /app/.venv volume is already seeded with exactly these deps.
CMD [".venv/bin/uvicorn", "guide.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
