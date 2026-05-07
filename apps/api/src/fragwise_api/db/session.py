"""Async SQLAlchemy engine + sessionmaker + FastAPI dependency."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _normalize(url: str) -> str:
    """Coerce a sync ``postgresql://`` URL to the asyncpg driver form."""
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def make_engine(url: str | None = None) -> AsyncEngine:
    """Construct an ``AsyncEngine`` from ``url`` or ``$DATABASE_URL``."""
    raw = url if url is not None else os.environ.get("DATABASE_URL")
    if not raw:
        raise RuntimeError("DATABASE_URL is required. Set it in your environment or .env.")
    return create_async_engine(_normalize(raw), pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Construct an ``async_sessionmaker`` bound to ``engine``."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an ``AsyncSession`` from app state."""
    sm: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    async with sm() as session:
        yield session
