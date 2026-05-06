"""FastAPI app factory + lifespan + /healthz + /readyz."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from fragwise_api.db.session import make_engine, make_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Construct the async engine + sessionmaker; dispose on shutdown."""
    engine = make_engine()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application."""
    app = FastAPI(title="Fragwise API", version="0.0.0", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        """Liveness probe. MUST NOT touch DB/Redis."""
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> Any:
        """Readiness probe. Runs ``SELECT 1`` via the lifespan-owned engine."""
        sm = app.state.db_sessionmaker
        try:
            async with sm() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "unready", "error": str(exc)[:200]},
            )

    return app


app = create_app()
