"""Brands list + detail. R2-W2: ILIKE wildcards in `?q=` are escaped."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload

from fragwise_api.db.models import Brand, Fragrance

from ..deps import DbSession
from ..errors import not_found
from ..filters import BrandListQueryDep, LimitOffsetDep
from ..pagination import paginate
from ..schemas.brand import BrandDetail
from ..schemas.common import ListEnvelope, Pagination
from ..schemas.fragrance import FragranceListItem
from ..schemas.summaries import BrandSummary

router = APIRouter(prefix="/brands", tags=["Brands"])

SLUG = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


def _escape_ilike(value: str) -> str:
    """R2-W2: escape backslash first, then SQL wildcards `%` and `_`."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=ListEnvelope[BrandSummary])
async def list_brands(
    session: DbSession,
    q: BrandListQueryDep,  # R3: matches FragranceListQueryDep pattern
) -> ListEnvelope[BrandSummary]:
    stmt: Select[Any] = select(Brand).order_by(Brand.name.asc(), Brand.id.asc())
    if q.q:
        escaped = _escape_ilike(q.q)
        stmt = stmt.where(Brand.name.ilike(f"%{escaped}%", escape="\\"))
    rows, total = await paginate(session, stmt, limit=q.limit, offset=q.offset)
    return ListEnvelope[BrandSummary](
        data=[BrandSummary.model_validate(r) for r in rows],
        pagination=Pagination(
            limit=q.limit,
            offset=q.offset,
            total=total,
            has_next=q.offset + q.limit < total,
        ),
    )


@router.get("/{slug}", response_model=BrandDetail)
async def get_brand(
    session: DbSession,
    slug: SLUG,
    page: LimitOffsetDep,
) -> BrandDetail:
    brand = (await session.execute(select(Brand).where(Brand.slug == slug))).scalar_one_or_none()
    if brand is None:
        raise not_found("Brand", slug)

    frag_stmt: Select[Any] = (
        select(Fragrance)
        .where(Fragrance.brand_id == brand.id)
        .options(joinedload(Fragrance.brand), joinedload(Fragrance.concentration))
        .order_by(Fragrance.name.asc(), Fragrance.id.asc())
    )
    rows, total = await paginate(session, frag_stmt, limit=page.limit, offset=page.offset)
    return BrandDetail(
        slug=brand.slug,
        name=brand.name,
        fragrances=ListEnvelope[FragranceListItem](
            data=[FragranceListItem.model_validate(r) for r in rows],
            pagination=Pagination(
                limit=page.limit,
                offset=page.offset,
                total=total,
                has_next=page.offset + page.limit < total,
            ),
        ),
    )
