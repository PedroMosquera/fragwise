"""FastAPI app factory + lifespan + /healthz + /readyz + /api/v1."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from fragwise_api.api.v1 import api_router
from fragwise_api.api.v1.errors import install_error_handlers
from fragwise_api.db.session import make_engine, make_sessionmaker

logger = logging.getLogger(__name__)

# Pinned (ADR-0022): NOT derived from pyproject.version. Bump deliberately.
OPENAPI_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Single source of truth for the engine + sessionmaker."""
    engine = make_engine()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)
    try:
        yield
    finally:
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_resolve_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    install_error_handlers(app)

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
    return app


app = create_app()
