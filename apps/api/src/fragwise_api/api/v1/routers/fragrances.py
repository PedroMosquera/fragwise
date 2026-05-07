"""GET /api/v1/fragrances and /api/v1/fragrances/{slug}."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload, selectinload

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

from ..deps import DbSession
from ..errors import not_found
from ..filters import FragranceListQuery, FragranceListQueryDep
from ..pagination import paginate
from ..schemas.common import ListEnvelope, Pagination
from ..schemas.fragrance import FragranceDetail, FragranceListItem, map_fragrance_detail

router = APIRouter(prefix="/fragrances", tags=["Fragrances"])

SLUG = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


def _apply_filters(stmt: Select[Any], f: FragranceListQuery) -> Select[Any]:
    """Compose WHERE clauses for FragranceListQuery.

    R3: compute normalized locals (do NOT mutate the Pydantic input model).
    R2-C5: strip empty strings from multi-value list filters so `?accord=`
    or trailing-comma typos don't reduce results to zero.

    C3: Multi-value M:M filters use IN-subqueries, not JOIN+DISTINCT.
    The IN-subquery pattern keeps the row set distinct without a global
    `.distinct()` and avoids plan blowups on large catalogs.
    """
    accord = [s for s in (f.accord or []) if s]
    perfumer = [s for s in (f.perfumer or []) if s]
    note = [s for s in (f.note or []) if s]

    if f.brand is not None:
        stmt = stmt.join(Brand, Brand.id == Fragrance.brand_id).where(Brand.slug == f.brand)
    if f.gender is not None:
        stmt = stmt.where(Fragrance.gender == f.gender)
    if f.year_min is not None:
        stmt = stmt.where(Fragrance.year_released >= f.year_min)
    if f.year_max is not None:
        stmt = stmt.where(Fragrance.year_released <= f.year_max)
    if f.concentration is not None:
        stmt = stmt.join(Concentration, Concentration.id == Fragrance.concentration_id).where(
            Concentration.slug == f.concentration
        )
    if perfumer:
        stmt = stmt.where(
            Fragrance.id.in_(
                select(FragrancePerfumer.fragrance_id).where(
                    FragrancePerfumer.perfumer_id.in_(
                        select(Perfumer.id).where(Perfumer.slug.in_(perfumer))
                    )
                )
            )
        )
    if accord:
        stmt = stmt.where(
            Fragrance.id.in_(
                select(FragranceAccord.fragrance_id).where(
                    FragranceAccord.accord_id.in_(select(Accord.id).where(Accord.slug.in_(accord)))
                )
            )
        )
    if note:
        stmt = stmt.where(
            Fragrance.id.in_(
                select(FragranceNote.fragrance_id).where(
                    FragranceNote.note_id.in_(select(Note.id).where(Note.slug.in_(note)))
                )
            )
        )
    return stmt  # NO global .distinct() — IN-subqueries already deduplicate


@router.get("", response_model=ListEnvelope[FragranceListItem])
async def list_fragrances(
    session: DbSession,
    query: FragranceListQueryDep,
) -> ListEnvelope[FragranceListItem]:
    stmt: Select[Any] = (
        select(Fragrance)
        .options(joinedload(Fragrance.brand), joinedload(Fragrance.concentration))
        .order_by(Fragrance.name.asc(), Fragrance.id.asc())  # S5 stable tiebreaker
    )
    stmt = _apply_filters(stmt, query)
    rows, total = await paginate(session, stmt, limit=query.limit, offset=query.offset)
    return ListEnvelope[FragranceListItem](
        data=[FragranceListItem.model_validate(r) for r in rows],
        pagination=Pagination(
            limit=query.limit,
            offset=query.offset,
            total=total,
            has_next=query.offset + query.limit < total,
        ),
    )


@router.get("/{slug}", response_model=FragranceDetail)
async def get_fragrance(session: DbSession, slug: SLUG) -> FragranceDetail:
    stmt = (
        select(Fragrance)
        .where(Fragrance.slug == slug)
        .options(
            joinedload(Fragrance.brand),
            joinedload(Fragrance.concentration),
            selectinload(Fragrance.perfumers),
            selectinload(Fragrance.fragrance_notes).selectinload(FragranceNote.note),
            selectinload(Fragrance.accords),
            selectinload(Fragrance.articles),
        )
    )
    frag = (await session.execute(stmt)).scalars().unique().one_or_none()
    if frag is None:
        raise not_found("Fragrance", slug)
    return map_fragrance_detail(frag)
