"""Filter Pydantic models for list endpoints.

Each list endpoint that supports both filters and pagination uses a single
**combined** query model (multi-inheritance from filters + LimitOffsetParams).
This is the W6 fix: FastAPI validates per-model with `extra="forbid"`, so two
separate `Annotated[..., Query()]` deps on the same endpoint produce false 422s.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field

from fragwise_api.db.enums import Gender

from .pagination import LimitOffsetParams


class FragranceFilters(BaseModel):
    model_config = {"extra": "forbid"}

    brand: str | None = Field(default=None)  # slug
    perfumer: list[str] | None = Field(default=None)  # slugs (OR)
    gender: Gender | None = Field(default=None)
    year_min: int | None = Field(default=None, ge=1700, le=2100)
    year_max: int | None = Field(default=None, ge=1700, le=2100)
    concentration: str | None = Field(default=None)  # slug
    accord: list[str] | None = Field(default=None, max_length=10)  # slugs (OR)
    note: list[str] | None = Field(default=None, max_length=20)  # slugs (OR)


class FragranceListQuery(FragranceFilters, LimitOffsetParams):
    """Combined filters + pagination for `GET /fragrances`."""

    model_config = {"extra": "forbid"}


class BrandFilters(BaseModel):
    model_config = {"extra": "forbid"}

    q: str | None = Field(default=None, max_length=100)  # case-insensitive substring on `name`


class BrandListQuery(BrandFilters, LimitOffsetParams):
    model_config = {"extra": "forbid"}


class PerfumerFilters(BaseModel):
    model_config = {"extra": "forbid"}

    q: str | None = Field(default=None, max_length=100)  # case-insensitive substring on `name`


class PerfumerListQuery(PerfumerFilters, LimitOffsetParams):
    model_config = {"extra": "forbid"}


# Detail endpoints with a paginated nested `fragrances` array reuse plain
# LimitOffsetParams (no filters) — see routers.
FragranceListQueryDep = Annotated[FragranceListQuery, Query()]
BrandListQueryDep = Annotated[BrandListQuery, Query()]
PerfumerListQueryDep = Annotated[PerfumerListQuery, Query()]
LimitOffsetDep = Annotated[LimitOffsetParams, Query()]
