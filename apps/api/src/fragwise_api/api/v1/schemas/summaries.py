"""Summary schemas — slim views shared across detail endpoints.

F1: This module exists to break the import cycle between
`schemas/fragrance.py` (which needs every Summary) and the per-resource
detail modules (which need `FragranceListItem`). `summaries.py` imports
nothing from sibling schema modules, so it is a clean dependency root.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrandSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class PerfumerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class NoteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class AccordSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class ConcentrationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class ArticleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    title: str
    published_at: datetime | None = None
