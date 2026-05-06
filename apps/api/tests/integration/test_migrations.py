"""Apply + rollback the initial migration; assert schema state."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[2]


def _alembic_cfg(database_url: str) -> Config:
    os.environ["DATABASE_URL"] = database_url
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    return cfg


@pytest.mark.asyncio
async def test_upgrade_creates_tables_and_extension(database_url: str, engine: AsyncEngine) -> None:
    cfg = _alembic_cfg(database_url)
    import asyncio as _asyncio

    await _asyncio.to_thread(command.upgrade, cfg, "head")
    async with engine.connect() as conn:
        tables = (
            (await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")))
            .scalars()
            .all()
        )
        for t in (
            "brands",
            "perfumers",
            "concentrations",
            "notes",
            "accords",
            "articles",
            "fragrances",
            "fragrance_notes",
            "fragrance_perfumers",
            "fragrance_articles",
            "fragrance_embeddings",
        ):
            assert t in tables, t

        ext = (
            await conn.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'"))
        ).scalar()
        assert ext == "vector"

        idx = (
            await conn.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename='fragrance_embeddings' "
                    "AND indexname='ix_fragrance_embeddings_hnsw'"
                )
            )
        ).scalar()
        assert idx is not None
        assert "hnsw" in idx
        assert "vector_cosine_ops" in idx

        # Concentrations seeded.
        seed_count = (await conn.execute(text("SELECT count(*) FROM concentrations"))).scalar()
        assert seed_count is not None and seed_count >= 5


@pytest.mark.asyncio
async def test_downgrade_empties_schema(database_url: str, engine: AsyncEngine) -> None:
    import asyncio as _asyncio

    cfg = _alembic_cfg(database_url)
    await _asyncio.to_thread(command.upgrade, cfg, "head")
    await _asyncio.to_thread(command.downgrade, cfg, "base")
    async with engine.connect() as conn:
        tables = (
            (await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")))
            .scalars()
            .all()
        )
        for t in (
            "brands",
            "fragrances",
            "fragrance_embeddings",
            "concentrations",
        ):
            assert t not in tables

        ext = (
            await conn.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'"))
        ).scalar()
        assert ext is None

        type_rows = (
            (
                await conn.execute(
                    text(
                        "SELECT typname FROM pg_type "
                        "WHERE typname IN "
                        "('fragrance_gender','fragrance_note_role')"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert type_rows == []
