"""FastAPI app factory + lifespan + /healthz."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook. Empty in 0b; 0c plugs in DB + Redis here."""
    yield


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application."""
    app = FastAPI(
        title="Fragwise API",
        version="0.0.0",
        lifespan=lifespan,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        """Liveness probe. MUST NOT touch DB/Redis (separate /readyz arrives in 0c)."""
        return {"status": "ok"}

    return app


app = create_app()
