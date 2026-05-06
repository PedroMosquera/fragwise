"""Integration test fixtures: pgvector testcontainer + per-test session."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

PGVECTOR_IMAGE = "pgvector/pgvector:pg16"


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PostgresContainer]:
    """Boot one pgvector container for the entire integration session."""
    with PostgresContainer(
        image=PGVECTOR_IMAGE,
        driver="asyncpg",
        username="fragwise",
        password="fragwise",
        dbname="fragwise",
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url(pg_container: PostgresContainer) -> str:
    """Expose the container's URL via env so Alembic + app can pick it up."""
    url = pg_container.get_connection_url()
    os.environ["DATABASE_URL"] = url
    return url


@pytest_asyncio.fixture()
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    """Function-scoped engine: asyncpg connections have event-loop affinity,
    and pytest-asyncio creates a fresh loop per test by default. A
    session-scoped engine would leak connections bound to a stale loop."""
    eng = create_async_engine(database_url)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture()
async def db_session(
    engine: AsyncEngine,
) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        yield session
