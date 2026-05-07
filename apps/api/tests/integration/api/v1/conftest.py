"""Integration test fixtures for /api/v1: schema bootstrap + seed + httpx client."""

from __future__ import annotations

import asyncio as _asyncio
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[4]


def _alembic_cfg(database_url: str) -> Config:
    os.environ["DATABASE_URL"] = database_url
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    return cfg


@pytest_asyncio.fixture(scope="module")
async def migrated_db(pg_container) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
    """Boot a clean DB at head for the module's tests."""
    url = pg_container.get_connection_url()
    os.environ["DATABASE_URL"] = url
    cfg = _alembic_cfg(url)
    await _asyncio.to_thread(command.downgrade, cfg, "base")
    await _asyncio.to_thread(command.upgrade, cfg, "head")
    yield url


@pytest_asyncio.fixture()
async def seed_engine(migrated_db: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(migrated_db)
    try:
        yield eng
    finally:
        await eng.dispose()


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest_asyncio.fixture()
async def seeded(seed_engine: AsyncEngine) -> AsyncIterator[dict[str, dict[str, uuid.UUID]]]:
    """Insert a deterministic mini fixture set and yield the slug->id maps.

    Uses raw SQL so the fixture is independent of the seed-script semantics.
    Each test starts with a TRUNCATE of the catalog tables so it is isolated.
    """
    async with seed_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE fragrance_accords, fragrance_articles, fragrance_perfumers, "
                "fragrance_notes, fragrance_embeddings, fragrances, articles, accords, notes, "
                "perfumers, brands RESTART IDENTITY CASCADE"
            )
        )

    sm = async_sessionmaker(seed_engine, expire_on_commit=False)

    brands = {"chanel": _new_uuid(), "dior": _new_uuid(), "creed": _new_uuid()}
    perfumers = {
        "jean-claude-ellena": _new_uuid(),
        "francis-kurkdjian": _new_uuid(),
    }
    accords = {
        "floral": _new_uuid(),
        "woody": _new_uuid(),
        "oriental": _new_uuid(),
        "gourmand": _new_uuid(),
        "aquatic": _new_uuid(),
        "fougere": _new_uuid(),
    }
    notes = {
        "citrus": _new_uuid(),
        "bergamot": _new_uuid(),
        "bergamot-mint": _new_uuid(),
        "jasmine": _new_uuid(),
        "rose": _new_uuid(),
        "vanilla": _new_uuid(),
    }
    fragrances = {
        "aventus": _new_uuid(),
        "no-5": _new_uuid(),
        "sauvage": _new_uuid(),
        "miss-dior": _new_uuid(),
        "homme": _new_uuid(),
    }
    articles = {"top-10-summer": _new_uuid()}

    async with sm() as session:
        for slug, bid in brands.items():
            await session.execute(
                text("INSERT INTO brands (id, slug, name) VALUES (:id, :slug, :name)"),
                {"id": bid, "slug": slug, "name": slug.title()},
            )

        for slug, pid in perfumers.items():
            await session.execute(
                text("INSERT INTO perfumers (id, slug, name) VALUES (:id, :slug, :name)"),
                {"id": pid, "slug": slug, "name": slug.replace("-", " ").title()},
            )

        for slug, aid in accords.items():
            await session.execute(
                text("INSERT INTO accords (id, slug, name) VALUES (:id, :slug, :name)"),
                {"id": aid, "slug": slug, "name": slug.title()},
            )

        # Notes — citrus parent of bergamot; bergamot parent of bergamot-mint.
        sql_note_root = "INSERT INTO notes (id, slug, name) VALUES (:id, :slug, :name)"
        for slug in ("citrus", "jasmine", "rose", "vanilla"):
            await session.execute(
                text(sql_note_root),
                {"id": notes[slug], "slug": slug, "name": slug.title()},
            )
        sql_note_child = (
            "INSERT INTO notes (id, slug, name, parent_id) VALUES (:id, :slug, :name, :pid)"
        )
        await session.execute(
            text(sql_note_child),
            {
                "id": notes["bergamot"],
                "slug": "bergamot",
                "name": "Bergamot",
                "pid": notes["citrus"],
            },
        )
        await session.execute(
            text(sql_note_child),
            {
                "id": notes["bergamot-mint"],
                "slug": "bergamot-mint",
                "name": "Bergamot Mint",
                "pid": notes["bergamot"],
            },
        )

        # Concentrations — already seeded by 0001 migration. Get edp id.
        conc_id = (
            await session.execute(text("SELECT id FROM concentrations WHERE slug='edp'"))
        ).scalar_one()

        # Fragrances. Brand/gender/year tuples per slug.
        frag_specs = [
            ("aventus", "Aventus", brands["creed"], "masc", 2010),
            ("no-5", "No 5", brands["chanel"], "fem", 1921),
            ("miss-dior", "Miss Dior", brands["chanel"], "fem", 2017),
            ("sauvage", "Sauvage", brands["dior"], "masc", 2015),
            ("homme", "Homme", brands["dior"], "masc", 2011),
        ]
        sql_frag = (
            "INSERT INTO fragrances "
            "(id, slug, name, brand_id, gender, year_released, "
            "concentration_id, description) "
            "VALUES (:id, :slug, :name, :bid, :gender, :year, :cid, :desc)"
        )
        for slug, name, bid, gender, year in frag_specs:
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
                    "desc": f"Test description for {name}",
                },
            )

        # Articles
        sql_article = (
            "INSERT INTO articles "
            "(id, slug, title, body, published_at) "
            "VALUES (:id, :slug, :title, :body, :pub)"
        )
        for slug, aid in articles.items():
            await session.execute(
                text(sql_article),
                {
                    "id": aid,
                    "slug": slug,
                    "title": "Top 10 Summer Fragrances",
                    "body": "Body content here.",
                    "pub": datetime(2024, 6, 1, tzinfo=UTC),
                },
            )

        # Joins. Build short helper rows then bulk-insert.
        f = fragrances
        a = accords
        p = perfumers
        n = notes
        ar = articles

        accord_pairs = [
            (f["aventus"], a["floral"]),
            (f["aventus"], a["woody"]),
            (f["no-5"], a["floral"]),
            (f["miss-dior"], a["floral"]),
            (f["sauvage"], a["woody"]),
            (f["homme"], a["woody"]),
        ]
        sql_acc = (
            "INSERT INTO fragrance_accords (id, fragrance_id, accord_id) VALUES (:id, :fid, :aid)"
        )
        for fid, aid in accord_pairs:
            await session.execute(
                text(sql_acc),
                {"id": _new_uuid(), "fid": fid, "aid": aid},
            )

        perfumer_pairs = [
            (f["aventus"], p["francis-kurkdjian"]),
            (f["no-5"], p["jean-claude-ellena"]),
            (f["miss-dior"], p["jean-claude-ellena"]),
            (f["sauvage"], p["francis-kurkdjian"]),
        ]
        sql_perf = (
            "INSERT INTO fragrance_perfumers (id, fragrance_id, perfumer_id) "
            "VALUES (:id, :fid, :pid)"
        )
        for fid, pid in perfumer_pairs:
            await session.execute(
                text(sql_perf),
                {"id": _new_uuid(), "fid": fid, "pid": pid},
            )

        note_rows = [
            (f["aventus"], n["jasmine"], "top"),
            (f["aventus"], n["rose"], "heart"),
            (f["aventus"], n["vanilla"], "base"),
            (f["no-5"], n["jasmine"], "top"),
            (f["miss-dior"], n["rose"], "top"),
            (f["sauvage"], n["vanilla"], "heart"),
        ]
        sql_fn = (
            "INSERT INTO fragrance_notes "
            "(id, fragrance_id, note_id, role, position) "
            "VALUES (:id, :fid, :nid, :role, 0)"
        )
        for fid, nid, role in note_rows:
            await session.execute(
                text(sql_fn),
                {"id": _new_uuid(), "fid": fid, "nid": nid, "role": role},
            )

        sql_fa = (
            "INSERT INTO fragrance_articles (id, fragrance_id, article_id) VALUES (:id, :fid, :aid)"
        )
        await session.execute(
            text(sql_fa),
            {
                "id": _new_uuid(),
                "fid": f["aventus"],
                "aid": ar["top-10-summer"],
            },
        )

        await session.commit()

    yield {
        "brands": brands,
        "perfumers": perfumers,
        "accords": accords,
        "notes": notes,
        "fragrances": fragrances,
        "articles": articles,
    }


@pytest_asyncio.fixture()
async def app_client(seed_engine: AsyncEngine, seeded: dict) -> AsyncIterator[httpx.AsyncClient]:
    """httpx ASGITransport client wired to a fresh app whose lifespan uses
    `seed_engine` (the same DB the seed fixture populated)."""
    from fragwise_api.db.session import make_sessionmaker
    from fragwise_api.main import create_app

    app = create_app()
    # Bypass the default lifespan so we use the test-owned engine.
    app.state.db_engine = seed_engine
    app.state.db_sessionmaker = make_sessionmaker(seed_engine)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def query_counter(seed_engine: AsyncEngine) -> Iterator[dict[str, int]]:
    """Counts SELECT statements issued via the test engine."""
    counts = {"selects": 0}

    def _on_exec(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        if statement.lstrip().upper().startswith("SELECT"):
            counts["selects"] += 1

    event.listen(seed_engine.sync_engine, "after_cursor_execute", _on_exec)
    try:
        yield counts
    finally:
        event.remove(seed_engine.sync_engine, "after_cursor_execute", _on_exec)
