"""Fragrance schemas. `id` is a UUID; Pydantic v2 serializes to string in JSON."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .summaries import (
    AccordSummary,
    ArticleSummary,
    BrandSummary,
    ConcentrationSummary,
    NoteSummary,
    PerfumerSummary,
)


class NotesByRole(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    top: list[NoteSummary] = []
    heart: list[NoteSummary] = []
    base: list[NoteSummary] = []


class FragranceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID  # C4: was `str`; ORM column is uuid.UUID
    slug: str
    name: str
    brand: BrandSummary
    year_released: int | None
    gender: str
    concentration: ConcentrationSummary | None


class FragranceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID  # C4
    slug: str
    name: str
    description: str | None
    year_released: int | None
    year_text: str | None
    gender: str
    brand: BrandSummary
    concentration: ConcentrationSummary | None
    perfumers: list[PerfumerSummary]
    notes: NotesByRole
    accords: list[AccordSummary]
    articles: list[ArticleSummary]


def map_fragrance_detail(frag: Any) -> FragranceDetail:
    """Build FragranceDetail from an eager-loaded Fragrance ORM object.

    `frag.fragrance_notes` is the list of FragranceNote association rows
    (eager-loaded via selectinload(Fragrance.fragrance_notes).selectinload(
    FragranceNote.note)). Group by `role` for the response shape. C4: do NOT
    convert `id` with str(); Pydantic v2 handles UUID -> string serialization.
    """
    by_role: dict[str, list[NoteSummary]] = {"top": [], "heart": [], "base": []}
    for fn in frag.fragrance_notes:
        by_role[fn.role.value].append(NoteSummary.model_validate(fn.note))
    return FragranceDetail(
        id=frag.id,
        slug=frag.slug,
        name=frag.name,
        description=frag.description,
        year_released=frag.year_released,
        year_text=frag.year_text,
        gender=frag.gender.value,
        brand=BrandSummary.model_validate(frag.brand),
        concentration=(
            ConcentrationSummary.model_validate(frag.concentration)
            if frag.concentration is not None
            else None
        ),
        perfumers=[PerfumerSummary.model_validate(p) for p in frag.perfumers],
        notes=NotesByRole(**by_role),
        accords=[AccordSummary.model_validate(a) for a in frag.accords],
        articles=[ArticleSummary.model_validate(a) for a in frag.articles],
    )
