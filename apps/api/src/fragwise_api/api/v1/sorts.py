"""Default sort constants per resource router.

NOTE: Phase 1 locks `name ASC` (or `title ASC` for articles, since Article has
no `name` column) on every list endpoint, plus a stable `id ASC` tiebreaker
on the UUID v7 PK to prevent row-shift between pages when same-name rows fall
on a page boundary (ADR-0021). Catalog UI may want `year_released DESC NULLS
LAST` later; flip the constant here per router when the UI change lands.
"""

from __future__ import annotations

DEFAULT_FRAGRANCE_SORT = "name_asc"  # then id ASC tiebreaker
DEFAULT_BRAND_SORT = "name_asc"
DEFAULT_PERFUMER_SORT = "name_asc"
DEFAULT_ACCORD_SORT = "name_asc"
DEFAULT_ARTICLE_SORT = "title_asc"  # Article has no `name` column
