"""Accord detail schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .common import ListEnvelope


class AccordDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    fragrances: ListEnvelope[FragranceListItem]


from .fragrance import FragranceListItem  # noqa: E402
