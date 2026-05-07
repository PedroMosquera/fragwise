"""Pydantic v2 request/response schemas for hybrid search.

`SearchHit.fragrance` is forward-referenced to `FragranceListItem` from the
P1 catalog schemas package. We rebuild the models at import time below so
that `model_validate` works without per-call pre-resolution. Order matters:
import `FragranceListItem`, then call `SearchHit.model_rebuild()`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fragwise_api.api.v1.schemas.fragrance import FragranceListItem

from .constants import DEFAULT_TOP_K, MAX_TOP_K


class FilterSpec(BaseModel):
    """Structured catalog filters; mirrors the P1 list-endpoint filters."""

    model_config = ConfigDict(extra="forbid")

    gender: Literal["masculine", "feminine", "unisex"] | None = None
    accord: list[str] = Field(default_factory=list)
    brand: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    concentration: str | None = None
    note: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    """`POST /api/v1/search` body."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=512)
    filters: FilterSpec = Field(default_factory=FilterSpec)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)
    include: list[Literal["notes", "brand", "perfumer"]] = Field(default_factory=list)


class SimilarRequest(BaseModel):
    """`POST /api/v1/fragrances/{slug}/similar` body."""

    model_config = ConfigDict(extra="forbid")

    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)
    include: list[Literal["notes", "brand", "perfumer"]] = Field(default_factory=list)


class SearchHit(BaseModel):
    """One ranked candidate in the search response."""

    model_config = ConfigDict(from_attributes=True)

    fragrance: FragranceListItem
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_reason: list[Literal["vector", "fts", "ontology"]]


class SearchResponse(BaseModel):
    """Envelope returned by both `/search` and `/{slug}/similar`."""

    model_config = ConfigDict(from_attributes=True)

    data: list[SearchHit]
    degraded: bool = False
    cache_hit: bool = False


# Pydantic v2: rebuild forward refs after the dependent classes are bound.
SearchHit.model_rebuild()
SearchResponse.model_rebuild()
