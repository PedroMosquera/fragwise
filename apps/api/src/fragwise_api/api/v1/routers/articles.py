"""Articles list + detail. Article uses `title` instead of `name` (W5)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path
from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload, selectinload

from fragwise_api.db.models import Article, Fragrance

from ..deps import DbSession
from ..errors import not_found
from ..filters import LimitOffsetDep
from ..pagination import paginate
from ..schemas.article import ArticleDetail
from ..schemas.common import ListEnvelope, Pagination
from ..schemas.fragrance import FragranceListItem
from ..schemas.summaries import ArticleSummary

router = APIRouter(prefix="/articles", tags=["Articles"])

SLUG = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


@router.get("", response_model=ListEnvelope[ArticleSummary])
async def list_articles(
    session: DbSession,
    page: LimitOffsetDep,
) -> ListEnvelope[ArticleSummary]:
    stmt: Select[Any] = select(Article).order_by(Article.title.asc(), Article.id.asc())
    rows, total = await paginate(session, stmt, limit=page.limit, offset=page.offset)
    return ListEnvelope[ArticleSummary](
        data=[ArticleSummary.model_validate(a) for a in rows],
        pagination=Pagination(
            limit=page.limit,
            offset=page.offset,
            total=total,
            has_next=page.offset + page.limit < total,
        ),
    )


@router.get("/{slug}", response_model=ArticleDetail)
async def get_article(session: DbSession, slug: SLUG) -> ArticleDetail:
    stmt = (
        select(Article)
        .where(Article.slug == slug)
        .options(
            selectinload(Article.fragrances).options(
                joinedload(Fragrance.brand),
                joinedload(Fragrance.concentration),
            )
        )
    )
    article = (await session.execute(stmt)).scalars().unique().one_or_none()
    if article is None:
        raise not_found("Article", slug)
    return ArticleDetail(
        slug=article.slug,
        title=article.title,
        body=article.body,
        published_at=article.published_at,
        fragrances=[FragranceListItem.model_validate(f) for f in article.fragrances],
    )
