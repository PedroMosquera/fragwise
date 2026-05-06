"""Idempotent UPSERT of notes + accords into the database.

Reads ``packages/ontology/{notes.yaml, accords.yaml}`` via the
``fragwise_api.ontology.loader`` and UPSERTs keyed on slug. Two-pass
on notes so ``parent_id`` resolves correctly.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from fragwise_api.db.base import _uuid7
from fragwise_api.db.models import Accord, Note
from fragwise_api.db.session import make_engine, make_sessionmaker
from fragwise_api.ontology.loader import load_accords, load_notes


async def _upsert_accords(session: AsyncSession) -> None:
    records = load_accords()
    if not records:
        return
    rows = [{"id": _uuid7(), "slug": a.slug, "name": a.name} for a in records]
    stmt = pg_insert(Accord.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"], set_={"name": stmt.excluded.name}
    )
    await session.execute(stmt)


async def _upsert_notes(session: AsyncSession) -> None:
    records = load_notes()
    if not records:
        return

    # Pass 1: insert all notes WITHOUT parent_id so parent rows definitely exist.
    base = [
        {"id": _uuid7(), "slug": n.slug, "name": n.name, "parent_id": None}
        for n in records
    ]
    stmt = pg_insert(Note.__table__).values(base)
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"], set_={"name": stmt.excluded.name}
    )
    await session.execute(stmt)

    # Pass 2: backfill parent_id by slug lookup.
    rows = (await session.execute(select(Note.slug, Note.id))).all()
    slug_to_id = {row.slug: row.id for row in rows}
    for n in records:
        new_parent = slug_to_id[n.parent_slug] if n.parent_slug else None
        await session.execute(
            Note.__table__.update()
            .where(Note.slug == n.slug)
            .values(parent_id=new_parent)
        )


async def main() -> None:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    async with sm() as session:
        await _upsert_accords(session)
        await _upsert_notes(session)
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
