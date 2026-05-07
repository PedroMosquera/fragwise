"""APIRouter for `POST /api/v1/search`.

`POST /api/v1/fragrances/{slug}/similar` lives in `api/v1/routers/fragrances.py`
to keep the URL space colocated with the existing P1 fragrances router. Both
handlers share the same retrieval pipeline via this module's helpers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fragwise_api.api.v1.errors import ApiError
from fragwise_api.api.v1.schemas.fragrance import FragranceListItem
from fragwise_api.db.models import Fragrance

from .cache import cache_key, get_cached, set_cached
from .daily_limit import (
    DailyLimitReached,
    daily_limit_value,
    increment_and_check,
    is_tripped,
)
from .embedder import embed_query
from .fallback import fts_only_retrieval
from .rate_limit import limiter, per_ip_rate
from .retrieval import RetrievalRow, hybrid_retrieve
from .schemas import (
    FilterSpec,
    SearchHit,
    SearchRequest,
    SearchResponse,
    SimilarRequest,
)

router = APIRouter(prefix="/api/v1", tags=["Search"])


# Dependency factories -------------------------------------------------------


async def get_session_dep(request: Request) -> AsyncIterator[AsyncSession]:
    sm = request.app.state.db_sessionmaker
    async with sm() as session:
        yield session


def get_redis_dep(request: Request) -> Redis:
    return request.app.state.redis  # type: ignore[no-any-return]


def get_openai_dep(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client  # type: ignore[no-any-return]


SessionDep = Annotated[AsyncSession, Depends(get_session_dep)]
RedisDep = Annotated[Redis, Depends(get_redis_dep)]
OpenAIDep = Annotated[AsyncOpenAI, Depends(get_openai_dep)]


# Daily kill-switch helper ---------------------------------------------------


def _kill_switch_error() -> ApiError:
    return ApiError(
        status_code=503,
        code="daily_limit_reached",
        message="daily search budget exhausted",
        detail=None,
    )


# Hit mapping ----------------------------------------------------------------


async def _load_list_items(session: AsyncSession, ids: list[UUID]) -> dict[UUID, FragranceListItem]:
    if not ids:
        return {}
    stmt = (
        select(Fragrance)
        .where(Fragrance.id.in_(ids))
        .options(joinedload(Fragrance.brand), joinedload(Fragrance.concentration))
    )
    rows = (await session.execute(stmt)).scalars().unique().all()
    return {row.id: FragranceListItem.model_validate(row) for row in rows}


async def _hits_for_rows(session: AsyncSession, rows: list[RetrievalRow]) -> list[SearchHit]:
    by_id = await _load_list_items(session, [r.fragrance_id for r in rows])
    out: list[SearchHit] = []
    for r in rows:
        item = by_id.get(r.fragrance_id)
        if item is None:
            # Race: row was deleted between retrieval and load. Skip.
            continue
        out.append(
            SearchHit(
                fragrance=item,
                relevance_score=r.relevance_score,
                match_reason=list(r.match_reason),  # type: ignore[arg-type]
            )
        )
    return out


# Core search handler --------------------------------------------------------


async def _handle_search(
    *,
    body: SearchRequest,
    session: AsyncSession,
    redis: Redis,
    openai_client: AsyncOpenAI,
) -> SearchResponse:
    now = datetime.now(UTC)
    limit = daily_limit_value()

    # Cache lookup BEFORE incrementing the daily counter (cache hits MUST NOT
    # consume the budget).
    key = cache_key(body)
    cached = await get_cached(redis, key)
    if cached is not None:
        # Still gate behind the kill-switch: if we're already tripped, we
        # treat that as a hard 503 even on cache-hit paths to prevent
        # cache-warming around a tripped budget.
        if await is_tripped(redis, limit, now):
            raise _kill_switch_error()
        cached["cache_hit"] = True
        return SearchResponse.model_validate(cached)

    # Fresh request — counts toward the daily budget.
    try:
        await increment_and_check(redis, limit, now)
    except DailyLimitReached as err:
        raise _kill_switch_error() from err

    # Try to embed the query; on failure → degraded FTS-only path.
    degraded = False
    rows: list[RetrievalRow]
    try:
        embedding = await embed_query(body.query, openai_client)
        rows = await hybrid_retrieve(
            session,
            query_embedding=embedding,
            query_text=body.query,
            filters=body.filters,
            top_k=body.top_k,
        )
    except (APIError, APITimeoutError, APIConnectionError):
        degraded = True
        rows = await fts_only_retrieval(
            session,
            query_text=body.query,
            filters=body.filters,
            top_k=body.top_k,
        )

    hits = await _hits_for_rows(session, rows)
    response = SearchResponse(data=hits, degraded=degraded, cache_hit=False)

    if not degraded:
        await set_cached(redis, key, response.model_dump(mode="json"))

    return response


# Routes ---------------------------------------------------------------------


@router.post("/search", response_model=SearchResponse)
@limiter.limit(per_ip_rate)  # callable → re-read env each request
async def search(
    request: Request,
    body: SearchRequest,
    session: SessionDep,
    redis: RedisDep,
    openai_client: OpenAIDep,
) -> SearchResponse:
    """Hybrid pgvector + FTS + ontology search."""
    return await _handle_search(
        body=body,
        session=session,
        redis=redis,
        openai_client=openai_client,
    )


# `_handle_similar` is shared with `routers/fragrances.py`; expose it here
# so that file just imports a single helper.


async def handle_similar(
    *,
    slug: str,
    body: SimilarRequest,
    session: AsyncSession,
    redis: Redis,
) -> SearchResponse:
    """Resolve a fragrance slug → its stored embedding → retrieval pipeline.

    No OpenAI call. 404 on unknown slug; 404 on missing embedding row.
    """
    from fragwise_api.api.v1.errors import not_found
    from fragwise_api.db.models import FragranceEmbedding

    from .constants import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, EMBEDDING_VIEW

    now = datetime.now(UTC)
    limit = daily_limit_value()

    # Resolve fragrance + load its embedding in one round trip via JOIN.
    stmt = select(Fragrance.id).where(Fragrance.slug == slug)
    frag_id = (await session.execute(stmt)).scalar_one_or_none()
    if frag_id is None:
        raise not_found("Fragrance", slug)

    emb_stmt = (
        select(FragranceEmbedding.embedding)
        .where(FragranceEmbedding.fragrance_id == frag_id)
        .where(FragranceEmbedding.view == EMBEDDING_VIEW)
        .where(FragranceEmbedding.model == EMBEDDING_MODEL)
        .where(FragranceEmbedding.dimensions == EMBEDDING_DIMENSIONS)
    )
    embedding = (await session.execute(emb_stmt)).scalar_one_or_none()
    if embedding is None:
        raise ApiError(
            status_code=404,
            code="not_found",
            message=f"Fragrance '{slug}' has no embedding",
            detail={"slug": slug},
        )

    # Daily kill-switch: similar consumes from the same global budget.
    try:
        await increment_and_check(redis, limit, now)
    except DailyLimitReached as err:
        raise _kill_switch_error() from err

    # pgvector → asyncpg returns embeddings as numpy arrays; cast to plain
    # Python floats so the SQL bind below renders cleanly.
    embedding_floats: list[float] = [float(x) for x in embedding]
    rows = await hybrid_retrieve(
        session,
        query_embedding=embedding_floats,
        query_text="",  # FTS branch short-circuits on empty query
        filters=FilterSpec(),
        top_k=body.top_k,
    )
    # Drop the source fragrance from its own similars list.
    rows = [r for r in rows if r.fragrance_id != frag_id]
    hits = await _hits_for_rows(session, rows)
    return SearchResponse(data=hits, degraded=False, cache_hit=False)
