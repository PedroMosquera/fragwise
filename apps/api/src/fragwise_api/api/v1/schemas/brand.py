"""Brand detail schema. Forward-ref to FragranceListItem resolved in schemas/__init__.py."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .common import ListEnvelope


class BrandDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    fragrances: ListEnvelope[FragranceListItem]  # forward ref; resolved centrally


# F1: Place FragranceListItem in this module's globals() so Pydantic's
# `eval_type_lenient` finds it via `module.__dict__` during model_rebuild().
from .fragrance import FragranceListItem  # noqa: E402

# DO NOT call `model_rebuild()` here. See schemas/__init__.py.
