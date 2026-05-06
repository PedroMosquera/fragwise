# syntax=docker/dockerfile:1.7

# ---- builder ------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.5-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

RUN uv python install 3.12

WORKDIR /app

# Install dependencies first (cache-friendly).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy project source and install it.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---- runtime ------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Create unprivileged user
RUN groupadd --system --gid 1001 fragwise \
 && useradd --system --uid 1001 --gid fragwise --home /app fragwise

WORKDIR /app

# Copy uv-managed Python and venv from the builder
COPY --from=builder /python /python
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER fragwise

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
  sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["uvicorn", "fragwise_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
