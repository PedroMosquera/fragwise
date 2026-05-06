"""Embed fragrances. Idempotent on source_hash. Tenacity-retried.

Workflow:
1. Load all fragrances joined to their notes (and brand + concentration).
2. Build canonical input text per fragrance.
3. Compute ``source_hash`` for each (matches the seed script).
4. Skip fragrances whose existing embedding row has a matching
   ``source_hash`` (and the same model + dimensions).
5. Batch up to 100 inputs per OpenAI ``embeddings.create`` call.
6. UPSERT into ``fragrance_embeddings`` keyed on
   ``(fragrance_id, view, model, dimensions)``.

REQUIRES ``OPENAI_API_KEY``. Exits non-zero with a clear error if missing.
NEVER invoked from CI — operator-only script.
"""

from __future__ import annotations

import asyncio
import os
import sys

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from fragwise_api.db import compute_source_hash
from fragwise_api.db.base import _uuid7
from fragwise_api.db.models import (
    Brand,
    Concentration,
    Fragrance,
    FragranceEmbedding,
    FragranceNote,
    Note,
)
from fragwise_api.db.session import make_engine, make_sessionmaker

MODEL = "text-embedding-3-small"
DIMENSIONS = 512
VIEW = "combined"
BATCH = 100


def _build_canonical_text(
    name: str,
    brand_name: str,
    concentration: str | None,
    notes_csv: str,
    description: str | None,
) -> str:
    return (
        f"{brand_name} {name} ({concentration or 'unknown'}). "
        f"Notes: {notes_csv}. {description or ''}"
    ).strip()


async def _embed_batch(
    client: AsyncOpenAI, inputs: list[str]
) -> list[list[float]]:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    ):
        with attempt:
            resp = await client.embeddings.create(
                model=MODEL, input=inputs, dimensions=DIMENSIONS
            )
            return [d.embedding for d in resp.data]
    raise RuntimeError("unreachable")


async def _load_state(session: AsyncSession) -> list[dict]:
    """Build a per-fragrance dict with name, brand, concentration, notes_csv,
    description, and the existing embedding's source_hash (if any)."""
    frag_rows = (
        await session.execute(
            select(
                Fragrance.id,
                Fragrance.slug,
                Fragrance.name,
                Fragrance.description,
                Brand.name.label("brand_name"),
                Concentration.slug.label("concentration_slug"),
            )
            .join(Brand, Brand.id == Fragrance.brand_id)
            .join(
                Concentration,
                Concentration.id == Fragrance.concentration_id,
                isouter=True,
            )
        )
    ).all()

    note_rows = (
        await session.execute(
            select(FragranceNote.fragrance_id, Note.slug).join(
                Note, Note.id == FragranceNote.note_id
            )
        )
    ).all()
    notes_by_frag: dict = {}
    for row in note_rows:
        notes_by_frag.setdefault(row.fragrance_id, set()).add(row.slug)

    existing_emb = (
        await session.execute(
            select(
                FragranceEmbedding.fragrance_id,
                FragranceEmbedding.source_hash,
                FragranceEmbedding.model,
                FragranceEmbedding.dimensions,
            ).where(
                FragranceEmbedding.view == VIEW,
                FragranceEmbedding.model == MODEL,
                FragranceEmbedding.dimensions == DIMENSIONS,
            )
        )
    ).all()
    hash_by_frag = {row.fragrance_id: row.source_hash for row in existing_emb}

    out: list[dict] = []
    for f in frag_rows:
        notes_csv = ",".join(sorted(notes_by_frag.get(f.id, set())))
        canonical = _build_canonical_text(
            name=f.name,
            brand_name=f.brand_name,
            concentration=f.concentration_slug,
            notes_csv=notes_csv,
            description=f.description,
        )
        h = compute_source_hash(f.name, f.description, notes_csv)
        out.append(
            {
                "fragrance_id": f.id,
                "slug": f.slug,
                "canonical_text": canonical,
                "source_hash": h,
                "existing_hash": hash_by_frag.get(f.id),
            }
        )
    return out


async def _upsert_embedding(
    session: AsyncSession,
    *,
    fragrance_id,
    embedding: list[float],
    source_hash: str,
) -> None:
    stmt = pg_insert(FragranceEmbedding.__table__).values(
        id=_uuid7(),
        fragrance_id=fragrance_id,
        view=VIEW,
        embedding=embedding,
        model=MODEL,
        dimensions=DIMENSIONS,
        source_hash=source_hash,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            "fragrance_id",
            "view",
            "model",
            "dimensions",
        ],
        set_={
            "embedding": stmt.excluded.embedding,
            "source_hash": stmt.excluded.source_hash,
        },
    )
    await session.execute(stmt)


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "ERROR: OPENAI_API_KEY is required to run embed_fragrances.py",
            file=sys.stderr,
        )
        sys.exit(2)

    client = AsyncOpenAI()
    engine = make_engine()
    sm = make_sessionmaker(engine)
    try:
        async with sm() as session:
            state = await _load_state(session)
            todo = [
                row
                for row in state
                if row["existing_hash"] != row["source_hash"]
            ]
            print(
                f"embed: {len(todo)} of {len(state)} fragrances "
                f"need (re)embedding"
            )
            for i in range(0, len(todo), BATCH):
                batch = todo[i : i + BATCH]
                vectors = await _embed_batch(
                    client, [row["canonical_text"] for row in batch]
                )
                for row, vec in zip(batch, vectors, strict=True):
                    await _upsert_embedding(
                        session,
                        fragrance_id=row["fragrance_id"],
                        embedding=vec,
                        source_hash=row["source_hash"],
                    )
            await session.commit()
    finally:
        await engine.dispose()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
