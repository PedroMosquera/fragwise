"""Centralized forward-ref resolution for v1 schemas.

Order: import every module so all classes are defined, then call
`model_rebuild(force=True)` on the detail schemas that contain forward refs.

R2-C2 / F1 design notes:
1. Pydantic v2 resolves forward refs against `module.__dict__` FIRST, so each
   detail-schema module must `from .fragrance import FragranceListItem` at
   the bottom of its own module to populate its `globals()`.
2. `model_rebuild()` may raise on classes that have no forward refs to
   resolve. We use `force=True` for idempotent re-imports AND we DROP
   `FragranceListItem` from the loop (it has no forward refs — all imports
   are concrete).
"""

from __future__ import annotations

# Import every schema module first so all classes are defined.
from . import (  # noqa: F401
    accord,
    article,
    brand,
    common,
    concentration,
    fragrance,
    note,
    perfumer,
    summaries,
)

for _model in (
    brand.BrandDetail,
    note.NoteDetail,
    note.NoteTreeNode,
    perfumer.PerfumerDetail,
    accord.AccordDetail,
    article.ArticleDetail,
):
    _model.model_rebuild(force=True)
