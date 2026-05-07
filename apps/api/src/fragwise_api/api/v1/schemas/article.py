"""Article detail schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .summaries import BrandSummary  # noqa: F401  (kept available for future expansion)


class ArticleDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    title: str
    body: str | None
    published_at: datetime | None
    fragrances: list[FragranceListItem]


from .fragrance import FragranceListItem  # noqa: E402
