"""Idempotent seed of ~10 example fragrances.

Reads ``data/seed/minimal_fragrances.yaml`` and UPSERTs:
- brands       (keyed on slug)
- perfumers    (keyed on slug)
- fragrances   (keyed on slug; updates name/year/gender/concentration/description)
- fragrance_notes      (keyed on (fragrance_id, note_id, role); diff-applied)
- fragrance_perfumers  (keyed on (fragrance_id, perfumer_id); diff-applied)
- fragrance_accords    (keyed on (fragrance_id, accord_id); diff-applied) [P1]
- notes.parent_id     (depth-2 hierarchy from notes_hierarchy block) [P1]

Notes referenced via slug MUST already exist (run ``just ingest`` first).
``source_hash`` per fragrance is computed via
``fragwise_api.db.compute_source_hash`` and shared with
``embed_fragrances.py``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from fragwise_api.db import compute_source_hash
from fragwise_api.db.base import _uuid7
from fragwise_api.db.enums import Gender, NoteRole
from fragwise_api.db.models import (
    Accord,
    Brand,
    Concentration,
    Fragrance,
    FragranceAccord,
    FragranceNote,
    FragrancePerfumer,
    Note,
    Perfumer,
)
from fragwise_api.db.session import make_engine, make_sessionmaker

SEED_PATH = (
    Path(__file__).resolve().parents[1] / "seed" / "minimal_fragrances.yaml"
)


async def _upsert_brand(session: AsyncSession, slug: str, name: str) -> None:
    stmt = pg_insert(Brand.__table__).values(
        id=_uuid7(), slug=slug, name=name
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"], set_={"name": stmt.excluded.name}
    )
    await session.execute(stmt)


async def _upsert_perfumer(session: AsyncSession, slug: str, name: str) -> None:
    stmt = pg_insert(Perfumer.__table__).values(
        id=_uuid7(), slug=slug, name=name
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"], set_={"name": stmt.excluded.name}
    )
    await session.execute(stmt)


async def _upsert_fragrance(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    brand_id: Any,
    year_released: int | None,
    year_text: str | None,
    gender: Gender,
    concentration_id: Any,
    description: str | None,
) -> None:
    stmt = pg_insert(Fragrance.__table__).values(
        id=_uuid7(),
        slug=slug,
        name=name,
        brand_id=brand_id,
        year_released=year_released,
        year_text=year_text,
        gender=gender.value,
        concentration_id=concentration_id,
        description=description,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"],
        set_={
            "name": stmt.excluded.name,
            "brand_id": stmt.excluded.brand_id,
            "year_released": stmt.excluded.year_released,
            "year_text": stmt.excluded.year_text,
            "gender": stmt.excluded.gender,
            "concentration_id": stmt.excluded.concentration_id,
            "description": stmt.excluded.description,
        },
    )
    await session.execute(stmt)


async def _sync_fragrance_notes(
    session: AsyncSession,
    *,
    fragrance_id: Any,
    desired: list[tuple[Any, NoteRole, int | None]],
) -> None:
    """Reconcile fragrance_notes to exactly `desired` for this fragrance."""
    existing = (
        await session.execute(
            select(
                FragranceNote.id,
                FragranceNote.note_id,
                FragranceNote.role,
            ).where(FragranceNote.fragrance_id == fragrance_id)
        )
    ).all()
    existing_keys = {(row.note_id, row.role) for row in existing}
    desired_keys = {(nid, role) for nid, role, _pos in desired}

    to_add = [
        {
            "id": _uuid7(),
            "fragrance_id": fragrance_id,
            "note_id": nid,
            "role": role.value,
            "position": pos,
        }
        for nid, role, pos in desired
        if (nid, role) not in existing_keys
    ]
    if to_add:
        await session.execute(
            pg_insert(FragranceNote.__table__).values(to_add)
        )

    for row in existing:
        if (row.note_id, row.role) not in desired_keys:
            await session.execute(
                FragranceNote.__table__.delete().where(
                    FragranceNote.id == row.id
                )
            )


async def _sync_fragrance_perfumers(
    session: AsyncSession, *, fragrance_id: Any, desired_perfumer_ids: list[Any]
) -> None:
    existing = (
        await session.execute(
            select(
                FragrancePerfumer.id, FragrancePerfumer.perfumer_id
            ).where(FragrancePerfumer.fragrance_id == fragrance_id)
        )
    ).all()
    existing_ids = {row.perfumer_id for row in existing}
    desired_ids = set(desired_perfumer_ids)

    to_add = [
        {
            "id": _uuid7(),
            "fragrance_id": fragrance_id,
            "perfumer_id": pid,
        }
        for pid in desired_perfumer_ids
        if pid not in existing_ids
    ]
    if to_add:
        await session.execute(
            pg_insert(FragrancePerfumer.__table__).values(to_add)
        )

    for row in existing:
        if row.perfumer_id not in desired_ids:
            await session.execute(
                FragrancePerfumer.__table__.delete().where(
                    FragrancePerfumer.id == row.id
                )
            )


async def _sync_fragrance_accords(
    session: AsyncSession, *, fragrance_id: Any, desired_accord_ids: list[Any]
) -> None:
    """P1: Reconcile fragrance_accords for this fragrance."""
    existing = (
        await session.execute(
            select(FragranceAccord.id, FragranceAccord.accord_id).where(
                FragranceAccord.fragrance_id == fragrance_id
            )
        )
    ).all()
    existing_ids = {row.accord_id for row in existing}
    desired_ids = set(desired_accord_ids)

    to_add = [
        {
            "id": _uuid7(),
            "fragrance_id": fragrance_id,
            "accord_id": aid,
        }
        for aid in desired_accord_ids
        if aid not in existing_ids
    ]
    if to_add:
        await session.execute(
            pg_insert(FragranceAccord.__table__).values(to_add)
        )

    for row in existing:
        if row.accord_id not in desired_ids:
            await session.execute(
                FragranceAccord.__table__.delete().where(
                    FragranceAccord.id == row.id
                )
            )


def _notes_csv(entry: dict[str, Any]) -> str:
    """Alphabetized comma-joined slug list across all roles. Matches embed."""
    notes_block = entry.get("notes") or {}
    all_slugs = []
    for role in ("top", "heart", "base"):
        all_slugs.extend(notes_block.get(role) or [])
    return ",".join(sorted(set(all_slugs)))


async def main() -> None:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    raw = yaml.safe_load(SEED_PATH.read_text())
    fragrances_data = raw.get("fragrances") or []
    notes_hierarchy = raw.get("notes_hierarchy") or {}

    async with sm() as session:
        # Concentration slug -> id map
        conc_rows = (
            await session.execute(
                select(Concentration.slug, Concentration.id)
            )
        ).all()
        conc_id_by_slug = {r.slug: r.id for r in conc_rows}

        # Pass 1: brands + perfumers
        for entry in fragrances_data:
            brand = entry["brand"]
            await _upsert_brand(session, brand["slug"], brand["name"])
            for p in entry.get("perfumers") or []:
                await _upsert_perfumer(session, p["slug"], p["name"])
        await session.flush()

        # Resolve brand + perfumer ids
        brand_rows = (
            await session.execute(select(Brand.slug, Brand.id))
        ).all()
        brand_id_by_slug = {r.slug: r.id for r in brand_rows}
        perf_rows = (
            await session.execute(select(Perfumer.slug, Perfumer.id))
        ).all()
        perf_id_by_slug = {r.slug: r.id for r in perf_rows}

        # Pass 2: fragrances
        for entry in fragrances_data:
            slug = entry["slug"]
            conc_slug = entry.get("concentration")
            await _upsert_fragrance(
                session,
                slug=slug,
                name=entry["name"],
                brand_id=brand_id_by_slug[entry["brand"]["slug"]],
                year_released=entry.get("year_released"),
                year_text=entry.get("year_text"),
                gender=Gender(entry["gender"]),
                concentration_id=(
                    conc_id_by_slug.get(conc_slug) if conc_slug else None
                ),
                description=entry.get("description"),
            )
        await session.flush()

        # Resolve fragrance ids
        frag_rows = (
            await session.execute(select(Fragrance.slug, Fragrance.id))
        ).all()
        frag_id_by_slug = {r.slug: r.id for r in frag_rows}

        # Resolve note + accord ids
        note_rows = (
            await session.execute(select(Note.slug, Note.id))
        ).all()
        note_id_by_slug = {r.slug: r.id for r in note_rows}
        accord_rows = (
            await session.execute(select(Accord.slug, Accord.id))
        ).all()
        accord_id_by_slug = {r.slug: r.id for r in accord_rows}

        # Pass 2b: depth-2 note hierarchy (P1 R2-W5)
        for parent_slug, child_slugs in notes_hierarchy.items():
            if parent_slug not in note_id_by_slug:
                # ontology may not seed every parent slug used here; skip
                # silently to keep the seed idempotent across ontology
                # versions.
                continue
            parent_id = note_id_by_slug[parent_slug]
            for child_slug in child_slugs or []:
                if child_slug not in note_id_by_slug:
                    continue
                await session.execute(
                    update(Note.__table__)
                    .where(Note.__table__.c.slug == child_slug)
                    .values(parent_id=parent_id)
                )

        # Pass 3: notes + perfumers + accords joins
        for entry in fragrances_data:
            fid = frag_id_by_slug[entry["slug"]]
            notes_block = entry.get("notes") or {}

            desired_notes: list[tuple[Any, NoteRole, int | None]] = []
            for role_str in ("top", "heart", "base"):
                slugs = notes_block.get(role_str) or []
                for pos, ns in enumerate(slugs):
                    if ns not in note_id_by_slug:
                        raise RuntimeError(
                            f"unknown note slug {ns!r} for {entry['slug']!r};"
                            " run `just ingest` first"
                        )
                    desired_notes.append(
                        (note_id_by_slug[ns], NoteRole(role_str), pos)
                    )
            await _sync_fragrance_notes(
                session, fragrance_id=fid, desired=desired_notes
            )

            desired_perfs = [
                perf_id_by_slug[p["slug"]]
                for p in (entry.get("perfumers") or [])
            ]
            await _sync_fragrance_perfumers(
                session,
                fragrance_id=fid,
                desired_perfumer_ids=desired_perfs,
            )

            # P1: accords
            desired_accords_ids = []
            for accord_slug in entry.get("accords") or []:
                if accord_slug not in accord_id_by_slug:
                    # ontology may not seed every accord slug; skip silently.
                    continue
                desired_accords_ids.append(accord_id_by_slug[accord_slug])
            await _sync_fragrance_accords(
                session,
                fragrance_id=fid,
                desired_accord_ids=desired_accords_ids,
            )

        # Compute source_hash per fragrance for downstream embed step.
        for entry in fragrances_data:
            h = compute_source_hash(
                entry["name"],
                entry.get("description"),
                _notes_csv(entry),
            )
            print(f"  source_hash[{entry['slug']}] = {h[:16]}...")

        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
