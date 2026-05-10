"""FastAPI app factory + lifespan + /healthz + /readyz + /api/v1."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis_asyncio
import tiktoken
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from fragwise_api.agent.rate_limit import chat_limiter, set_chat_storage_uri
from fragwise_api.agent.router import router as chat_router
from fragwise_api.api.v1 import api_router
from fragwise_api.api.v1.errors import install_error_handlers
from fragwise_api.db.session import make_engine, make_sessionmaker
from fragwise_api.search.rate_limit import (
    limiter,
    rate_limit_exceeded_handler,
    set_storage_uri,
)
from fragwise_api.search.router import router as search_router

logger = logging.getLogger(__name__)

# Pinned (ADR-0022): NOT derived from pyproject.version. Bump deliberately.
OPENAPI_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Single source of truth for engine + Redis + OpenAI + slowapi limiter.

    P0c established the engine/sessionmaker. P2 layers on:
      - `app.state.redis`: shared `redis.asyncio.Redis` for cache + counters
      - `app.state.openai_client`: shared `AsyncOpenAI` for query embeddings
      - `app.state.limiter`: slowapi `Limiter` backed by the same Redis URL
    """
    engine = make_engine()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    app.state.redis = redis_asyncio.Redis.from_url(redis_url, decode_responses=False)
    # AsyncOpenAI raises if `OPENAI_API_KEY` is unset; allow a placeholder
    # so test environments and dev probes (e.g. /readyz) can boot the app
    # without an embedding API key. Real embed calls still fail loudly.
    openai_key = os.environ.get("OPENAI_API_KEY", "test-placeholder-not-real")
    app.state.openai_client = AsyncOpenAI(api_key=openai_key)
    # Rebind the module-level limiter's storage so the decorators applied
    # at route-definition time pick up the prod Redis URL.
    set_storage_uri(redis_url)
    app.state.limiter = limiter
    # P3: chat limiter shares the same Redis URL but lives on a separate
    # `Limiter` instance so the chat-specific multi-window decorators
    # (5/h AND 20/d) don't leak into the search route's budget.
    set_chat_storage_uri(redis_url)
    app.state.chat_limiter = chat_limiter
    # ADR-0038: cache the tiktoken encoder at lifespan; reused across
    # requests. `gpt-4o-mini` resolves to `o200k_base`.
    app.state.tiktoken_encoder = tiktoken.encoding_for_model("gpt-4o-mini")

    try:
        yield
    finally:
        await app.state.openai_client.close()
        await app.state.redis.aclose()
        await engine.dispose()


def _resolve_cors_origins() -> list[str]:
    """ADR-0024: precedence CORS_ALLOW_ORIGIN, then NEXT_PUBLIC_API_URL, then *.

    Comma-separated values are split + stripped. R2-W1: if the parsed list
    is empty (e.g. raw was only whitespace/commas), fall back to ["*"].
    """
    raw = os.environ.get("CORS_ALLOW_ORIGIN") or os.environ.get("NEXT_PUBLIC_API_URL") or "*"
    parsed = [o.strip() for o in raw.split(",") if o.strip()]
    return parsed or ["*"]


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application."""
    app = FastAPI(
        title="Fragwise API",
        version=OPENAPI_VERSION,
        lifespan=lifespan,
        redirect_slashes=False,
    )

    # F6: allow_origins=["*"] is only valid because allow_credentials=False;
    # if credentials are ever enabled, replace with explicit dev origins.
    # POST is required for /api/v1/chat (P3 SSE) — preflight rejects the
    # browser fetch otherwise.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_resolve_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    # P2: slowapi raises RateLimitExceeded on overage; map it to our envelope.
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        """Liveness probe. MUST NOT touch DB/Redis."""
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> Any:
        """Readiness probe. S7: error message is generic; full exception is
        logged server-side so connection strings, hostnames, or driver-leaked
        credentials never reach the response body."""
        sm = app.state.db_sessionmaker
        try:
            async with sm() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            logger.exception("readyz: database probe failed")
            return JSONResponse(
                status_code=503,
                content={"status": "unready", "error": "database unreachable"},
            )

    app.include_router(api_router)
    # P2: hybrid search endpoints (router prefix is `/api/v1`).
    app.include_router(search_router)
    # P3: chat endpoint (router prefix is `/api/v1`).
    app.include_router(chat_router)
    return app


app = create_app()
