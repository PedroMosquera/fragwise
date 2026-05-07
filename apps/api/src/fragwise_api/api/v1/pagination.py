"""Offset+limit pagination params + helper."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class LimitOffsetParams(BaseModel):
    """Pagination query params; injected as part of a combined query model."""

    model_config = {"extra": "forbid"}

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


# NOTE: do NOT use `Annotated[LimitOffsetParams, Query()]` standalone alongside
# another `Annotated[XxxFilters, Query()]` on the same endpoint. FastAPI
# validates each model independently with `extra="forbid"`, so a key valid for
# one (e.g. `?brand=`) becomes "extra" to the other and yields a false 422.
# Compose a single per-endpoint query model that inherits both — see filters.py.


async def paginate(
    session: AsyncSession,
    stmt: Select[Any],
    *,
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    """Run a count(*) query then a windowed row query. Two round-trips total.

    Rationale (ADR-0023): a separate count is clearer than func.count().over()
    and avoids per-row aggregation cost.

    R3 fix: `count_stmt = select(func.count()).select_from(stmt.subquery())`
    counts rows of the filtered subquery. The earlier "double subquery" with
    `select(pk_column).select_from(stmt.subquery())` introduced `pk_column`'s
    table as an implicit FROM, producing a Cartesian product. The simple
    pattern is correct: `stmt.subquery()` materializes the FROM (with any
    JOINs), and `count(*)` counts its rows.

    Race condition: the count and the row query are two separate statements;
    a concurrent insert/delete can cause `total` and `len(data)` to disagree
    by ±1. ADR-0023 documents this as accepted; do not "fix" it without a
    spec change.
    """
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    rows_stmt = stmt.limit(limit).offset(offset)
    rows = list((await session.execute(rows_stmt)).scalars().unique().all())
    return rows, int(total)
