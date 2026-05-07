"""Integration test fixtures for hybrid search.

Reuses the testcontainers Postgres from the parent integration conftest;
swaps Redis for `fakeredis.aioredis.FakeRedis` (ADR-0030) and OpenAI for
an `AsyncMock` returning a deterministic 512-dim embedding.

The seeded fixture inserts a tiny set of fragrances WITH their stored
embeddings so vector searches return rows. Tests that need empty embedding
catalogs use a separate fixture (see `test_search_no_embeddings.py`).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis as fakeredis_async
import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[3]


def _alembic_cfg(database_url: str) -> Config:
    os.environ["DATABASE_URL"] = database_url
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    return cfg


@pytest_asyncio.fixture(scope="module")
async def search_migrated_db(pg_container) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
    """Boot a clean DB at head for the search test module."""
    import asyncio as _asyncio

    url = pg_container.get_connection_url()
    os.environ["DATABASE_URL"] = url
    cfg = _alembic_cfg(url)
    await _asyncio.to_thread(command.downgrade, cfg, "base")
    await _asyncio.to_thread(command.upgrade, cfg, "head")
    yield url


@pytest_asyncio.fixture()
async def search_engine(search_migrated_db: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(search_migrated_db)
    try:
        yield eng
    finally:
        await eng.dispose()


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _embedding_for(seed: int, dims: int = 512) -> list[float]:
    """Deterministic, distinct unit vectors so cosine ordering is meaningful."""
    # Simple basis-flavoured vectors: index `seed % dims` is 1, others 0.
    vec = [0.0] * dims
    vec[seed % dims] = 1.0
    return vec


@pytest_asyncio.fixture()
async def search_seeded(
    search_engine: AsyncEngine,
) -> AsyncIterator[dict[str, Any]]:
    """Seed a tiny catalog with embeddings keyed off `(model, view, dims)`."""
    from fragwise_api.search.constants import (
        EMBEDDING_DIMENSIONS,
        EMBEDDING_MODEL,
        EMBEDDING_VIEW,
    )

    async with search_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE fragrance_accords, fragrance_articles, "
                "fragrance_perfumers, fragrance_notes, fragrance_embeddings, "
                "fragrances, articles, accords, notes, perfumers, brands "
                "RESTART IDENTITY CASCADE"
            )
        )

    sm = async_sessionmaker(search_engine, expire_on_commit=False)

    brands = {"creed": _new_uuid(), "chanel": _new_uuid(), "dior": _new_uuid()}
    accords = {"smoky": _new_uuid(), "leather": _new_uuid(), "floral": _new_uuid()}
    fragrances = {
        "aventus": _new_uuid(),  # masc, smoky+leather, has embedding
        "no-5": _new_uuid(),  # fem, floral, has embedding
        "miss-dior": _new_uuid(),  # fem, floral, has embedding
        "sauvage": _new_uuid(),  # masc, smoky, has embedding
        "legacy": _new_uuid(),  # masc, NO embedding (for missing-embedding test)
    }

    async with sm() as session:
        for slug, bid in brands.items():
            await session.execute(
                text("INSERT INTO brands (id, slug, name) VALUES (:id, :slug, :name)"),
                {"id": bid, "slug": slug, "name": slug.title()},
            )
        for slug, aid in accords.items():
            await session.execute(
                text("INSERT INTO accords (id, slug, name) VALUES (:id, :slug, :name)"),
                {"id": aid, "slug": slug, "name": slug.title()},
            )

        conc_id = (
            await session.execute(text("SELECT id FROM concentrations WHERE slug='edp'"))
        ).scalar_one()

        frag_specs = [
            (
                "aventus",
                "Aventus",
                brands["creed"],
                "masc",
                2010,
                "smoky leather pineapple",
            ),
            ("no-5", "No 5", brands["chanel"], "fem", 1921, "floral aldehyde rose"),
            (
                "miss-dior",
                "Miss Dior",
                brands["chanel"],
                "fem",
                2017,
                "fresh floral peony",
            ),
            (
                "sauvage",
                "Sauvage",
                brands["dior"],
                "masc",
                2015,
                "smoky woody bergamot",
            ),
            (
                "legacy",
                "Legacy",
                brands["dior"],
                "masc",
                2000,
                "vintage classic",
            ),
        ]
        sql_frag = (
            "INSERT INTO fragrances "
            "(id, slug, name, brand_id, gender, year_released, "
            "concentration_id, description) "
            "VALUES (:id, :slug, :name, :bid, :gender, :year, :cid, :desc)"
        )
        for slug, name, bid, gender, year, desc in frag_specs:
            await session.execute(
                text(sql_frag),
                {
                    "id": fragrances[slug],
                    "slug": slug,
                    "name": name,
                    "bid": bid,
                    "gender": gender,
                    "year": year,
                    "cid": conc_id,
                    "desc": desc,
                },
            )

        accord_pairs = [
            (fragrances["aventus"], accords["smoky"]),
            (fragrances["aventus"], accords["leather"]),
            (fragrances["sauvage"], accords["smoky"]),
            (fragrances["no-5"], accords["floral"]),
            (fragrances["miss-dior"], accords["floral"]),
        ]
        sql_acc = (
            "INSERT INTO fragrance_accords (id, fragrance_id, accord_id) VALUES (:id, :fid, :aid)"
        )
        for fid, aid in accord_pairs:
            await session.execute(
                text(sql_acc),
                {"id": _new_uuid(), "fid": fid, "aid": aid},
            )

        # Embeddings: aventus, no-5, miss-dior, sauvage have embeddings.
        # legacy does NOT — used to test the missing-embedding 404 path.
        embedded = ["aventus", "no-5", "miss-dior", "sauvage"]
        sql_emb = (
            "INSERT INTO fragrance_embeddings "
            "(id, fragrance_id, view, embedding, model, dimensions, source_hash) "
            "VALUES (:id, :fid, :view, CAST(:emb AS vector(512)), :model, :dims, :hash)"
        )
        for i, slug in enumerate(embedded):
            await session.execute(
                text(sql_emb),
                {
                    "id": _new_uuid(),
                    "fid": fragrances[slug],
                    "view": EMBEDDING_VIEW,
                    "emb": str(_embedding_for(i)),
                    "model": EMBEDDING_MODEL,
                    "dims": EMBEDDING_DIMENSIONS,
                    "hash": f"hash-{slug}",
                },
            )

        await session.commit()

    yield {
        "brands": brands,
        "accords": accords,
        "fragrances": fragrances,
    }


@pytest.fixture()
def fake_redis() -> Iterator[fakeredis_async.FakeRedis]:
    """Per-test fakeredis. Limiter shares the same instance via app.state."""
    r = fakeredis_async.FakeRedis()
    yield r


@pytest.fixture()
def fake_openai() -> MagicMock:
    """AsyncOpenAI mock returning a deterministic 512-dim embedding."""
    client = MagicMock()
    client.close = AsyncMock(return_value=None)

    embeddings = MagicMock()

    async def _create(**kwargs: Any) -> Any:
        item = MagicMock()
        item.embedding = _embedding_for(0)  # rank "aventus" first
        resp = MagicMock()
        resp.data = [item]
        return resp

    embeddings.create = AsyncMock(side_effect=_create)
    client.embeddings = embeddings
    return client


def _make_app_with_overrides(
    engine: AsyncEngine,
    redis_client: Any,
    openai_client: Any,
) -> Any:
    """Build a fresh app whose lifespan was bypassed; inject test doubles."""
    from fragwise_api.db.session import make_sessionmaker
    from fragwise_api.main import create_app
    from fragwise_api.search.rate_limit import limiter, set_storage_uri

    # Reset per-IP rate state between tests by pointing slowapi at a fresh
    # in-memory backend. Each test gets a clean limiter window.
    set_storage_uri("memory://")
    limiter.reset()

    app = create_app()
    app.state.db_engine = engine
    app.state.db_sessionmaker = make_sessionmaker(engine)
    app.state.redis = redis_client
    app.state.openai_client = openai_client
    app.state.limiter = limiter
    return app


@pytest_asyncio.fixture()
async def search_client(
    search_engine: AsyncEngine,
    search_seeded: dict,
    fake_redis: Any,
    fake_openai: Any,
) -> AsyncIterator[httpx.AsyncClient]:
    app = _make_app_with_overrides(search_engine, fake_redis, fake_openai)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def now_utc() -> datetime:
    return datetime.now(UTC)
