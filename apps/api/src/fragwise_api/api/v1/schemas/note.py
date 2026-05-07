"""Note schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .common import ListEnvelope
from .summaries import NoteSummary


class NoteTreeNode(BaseModel):
    """Self-recursive tree node used by GET /api/v1/notes."""

    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    # F1 hygiene: use Field(default_factory=list) to avoid mutable-default
    # pitfall on a recursive model.
    children: list[NoteTreeNode] = Field(default_factory=list)


class NoteTreeEnvelope(BaseModel):
    data: list[NoteTreeNode]


class NoteDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    parent: NoteSummary | None
    fragrances: ListEnvelope[FragranceListItem]


from .fragrance import FragranceListItem  # noqa: E402
