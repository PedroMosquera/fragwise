"""Accords flat list + detail. Spec: list has no pagination."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path
from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload

from fragwise_api.db.models import Accord, Fragrance, FragranceAccord

from ..deps import DbSession
from ..errors import not_found
from ..filters import LimitOffsetDep
from ..pagination import paginate
from ..schemas.accord import AccordDetail
from ..schemas.common import ListEnvelope, Pagination
from ..schemas.fragrance import FragranceListItem
from ..schemas.summaries import AccordSummary

router = APIRouter(prefix="/accords", tags=["Accords"])

SLUG = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


class AccordsListResponse(BaseModel):
    data: list[AccordSummary]


@router.get("", response_model=AccordsListResponse)
async def list_accords(session: DbSession) -> AccordsListResponse:
    stmt: Select[Any] = select(Accord).order_by(Accord.name.asc(), Accord.id.asc())
    rows = list((await session.execute(stmt)).scalars().all())
    return AccordsListResponse(data=[AccordSummary.model_validate(a) for a in rows])


@router.get("/{slug}", response_model=AccordDetail)
async def get_accord(
    session: DbSession,
    slug: SLUG,
    page: LimitOffsetDep,
) -> AccordDetail:
    accord = (await session.execute(select(Accord).where(Accord.slug == slug))).scalar_one_or_none()
    if accord is None:
        raise not_found("Accord", slug)

    frag_stmt: Select[Any] = (
        select(Fragrance)
        .where(
            Fragrance.id.in_(
                select(FragranceAccord.fragrance_id).where(FragranceAccord.accord_id == accord.id)
            )
        )
        .options(joinedload(Fragrance.brand), joinedload(Fragrance.concentration))
        .order_by(Fragrance.name.asc(), Fragrance.id.asc())
    )
    rows, total = await paginate(session, frag_stmt, limit=page.limit, offset=page.offset)
    return AccordDetail(
        slug=accord.slug,
        name=accord.name,
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
