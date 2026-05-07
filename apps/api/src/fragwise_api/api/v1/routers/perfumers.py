"""Perfumers list + detail. R2-W2: ILIKE wildcards in `?q=` are escaped."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload

from fragwise_api.db.models import Fragrance, FragrancePerfumer, Perfumer

from ..deps import DbSession
from ..errors import not_found
from ..filters import LimitOffsetDep, PerfumerListQueryDep
from ..pagination import paginate
from ..schemas.common import ListEnvelope, Pagination
from ..schemas.fragrance import FragranceListItem
from ..schemas.perfumer import PerfumerDetail
from ..schemas.summaries import PerfumerSummary

router = APIRouter(prefix="/perfumers", tags=["Perfumers"])

SLUG = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


def _escape_ilike(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=ListEnvelope[PerfumerSummary])
async def list_perfumers(
    session: DbSession,
    q: PerfumerListQueryDep,
) -> ListEnvelope[PerfumerSummary]:
    stmt: Select[Any] = select(Perfumer).order_by(Perfumer.name.asc(), Perfumer.id.asc())
    if q.q:
        escaped = _escape_ilike(q.q)
        stmt = stmt.where(Perfumer.name.ilike(f"%{escaped}%", escape="\\"))
    rows, total = await paginate(session, stmt, limit=q.limit, offset=q.offset)
    return ListEnvelope[PerfumerSummary](
        data=[PerfumerSummary.model_validate(r) for r in rows],
        pagination=Pagination(
            limit=q.limit,
            offset=q.offset,
            total=total,
            has_next=q.offset + q.limit < total,
        ),
    )


@router.get("/{slug}", response_model=PerfumerDetail)
async def get_perfumer(
    session: DbSession,
    slug: SLUG,
    page: LimitOffsetDep,
) -> PerfumerDetail:
    perfumer = (
        await session.execute(select(Perfumer).where(Perfumer.slug == slug))
    ).scalar_one_or_none()
    if perfumer is None:
        raise not_found("Perfumer", slug)

    frag_stmt: Select[Any] = (
        select(Fragrance)
        .where(
            Fragrance.id.in_(
                select(FragrancePerfumer.fragrance_id).where(
                    FragrancePerfumer.perfumer_id == perfumer.id
                )
            )
        )
        .options(joinedload(Fragrance.brand), joinedload(Fragrance.concentration))
        .order_by(Fragrance.name.asc(), Fragrance.id.asc())
    )
    rows, total = await paginate(session, frag_stmt, limit=page.limit, offset=page.offset)
    return PerfumerDetail(
        slug=perfumer.slug,
        name=perfumer.name,
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
