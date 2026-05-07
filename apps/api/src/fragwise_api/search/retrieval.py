"""DB-side hybrid retrieval: pgvector + FTS + ontology fused via RRF.

ADR-0026: a single SQL round trip with filter pushdown on the base CTEs.
No Python-side merging. ADR-0032: `SET LOCAL hnsw.ef_search` is issued once
per transaction (the SQL runs in one `connection.execute` block) and is
scoped to that transaction by Postgres semantics.

Output is a list of `RetrievalRow` dataclasses; the router maps them into
`SearchHit` after loading the list-shape `FragranceListItem` rows.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .constants import DEFAULT_HNSW_EF_SEARCH, RRF_K
from .schemas import FilterSpec


@dataclass(frozen=True)
class RetrievalRow:
    """Result of one retrieval call (pre-mapping to FragranceListItem)."""

    fragrance_id: UUID
    relevance_score: float
    match_reason: list[str]


def _ef_search_value() -> int:
    raw = os.environ.get("FRAGWISE_HNSW_EF_SEARCH")
    if raw is None:
        return DEFAULT_HNSW_EF_SEARCH
    try:
        v = int(raw)
        if v <= 0:
            return DEFAULT_HNSW_EF_SEARCH
        return v
    except ValueError:
        return DEFAULT_HNSW_EF_SEARCH


def _ontology_active(filters: FilterSpec) -> bool:
    """Whether the response should tag `match_reason=['ontology', ...]`.

    Any structured filter (gender/brand/year/concentration/accord/note)
    counts as an ontology signal contributing to ranking.
    """
    return bool(
        filters.gender
        or filters.brand
        or filters.accord
        or filters.note
        or filters.year_min is not None
        or filters.year_max is not None
        or filters.concentration
    )


# Maximum theoretical RRF score for a single hit appearing at rank 1 in
# both vector and FTS branches: 1/(k+1) + 1/(k+1) = 2/(k+1).
_MAX_RRF = 2.0 / (RRF_K + 1)


def _normalize(score: float) -> float:
    """Map RRF score to [0, 1] using the fixed denominator (design Open Q1)."""
    if score <= 0:
        return 0.0
    return min(1.0, score / _MAX_RRF)


_GENDER_MAP: dict[str, str] = {
    "masculine": "masc",
    "feminine": "fem",
    "unisex": "unisex",
}


def _filter_params(filters: FilterSpec) -> dict[str, Any]:
    """Bind values for the filter CTE.

    The schema accepts the human-readable `masculine`/`feminine`/`unisex`
    enum, but the DB stores the abbreviated `masc`/`fem`/`unisex`/`genderfree`
    values. Map here before binding.
    """
    gender = _GENDER_MAP.get(filters.gender) if filters.gender else None
    return {
        "gender": gender,
        "brand_slug": filters.brand,
        "year_min": filters.year_min,
        "year_max": filters.year_max,
        "concentration_slug": filters.concentration,
        "accord_slugs": list(filters.accord) if filters.accord else None,
        "note_slugs": list(filters.note) if filters.note else None,
    }


# Filter CTE shared by all retrieval paths; the WHERE clauses are predicates
# not joins, which keeps the row set small before either FTS or vector scans.
_FILTERED_CTE = """
filtered AS (
  SELECT f.id
  FROM fragrances f
  LEFT JOIN concentrations c ON c.id = f.concentration_id
  WHERE (CAST(:gender AS fragrance_gender) IS NULL OR f.gender = CAST(:gender AS fragrance_gender))
    AND (CAST(:brand_slug AS text) IS NULL OR f.brand_id = (
        SELECT id FROM brands WHERE slug = :brand_slug))
    AND (CAST(:year_min AS int) IS NULL OR f.year_released >= :year_min)
    AND (CAST(:year_max AS int) IS NULL OR f.year_released <= :year_max)
    AND (CAST(:concentration_slug AS text) IS NULL OR c.slug = :concentration_slug)
    AND (CAST(:accord_slugs AS text[]) IS NULL OR EXISTS (
        SELECT 1 FROM fragrance_accords fa
        JOIN accords a ON a.id = fa.accord_id
        WHERE fa.fragrance_id = f.id AND a.slug = ANY(:accord_slugs)))
    AND (CAST(:note_slugs AS text[]) IS NULL OR EXISTS (
        SELECT 1 FROM fragrance_notes fn
        JOIN notes n ON n.id = fn.note_id
        WHERE fn.fragrance_id = f.id AND n.slug = ANY(:note_slugs)))
)
"""


_HYBRID_SQL = (
    "WITH "
    + _FILTERED_CTE
    + """,
vector_cte AS (
  SELECT e.fragrance_id,
         ROW_NUMBER() OVER (ORDER BY e.embedding <=> CAST(:query_embedding AS vector(512)))
           AS rank_v
  FROM fragrance_embeddings e
  JOIN filtered ff ON ff.id = e.fragrance_id
  WHERE e.view = :view AND e.model = :model AND e.dimensions = :dims
  ORDER BY e.embedding <=> CAST(:query_embedding AS vector(512))
  LIMIT 100
),
fts_cte AS (
  SELECT f.id AS fragrance_id,
         ROW_NUMBER() OVER (
           ORDER BY ts_rank_cd(
             to_tsvector('english', f.name || ' ' || coalesce(f.description, '')),
             plainto_tsquery('english', CAST(:query_text AS text))
           ) DESC
         ) AS rank_f
  FROM fragrances f
  JOIN filtered ff ON ff.id = f.id
  WHERE CAST(:query_text AS text) IS NOT NULL AND CAST(:query_text AS text) <> ''
    AND to_tsvector('english', f.name || ' ' || coalesce(f.description, ''))
        @@ plainto_tsquery('english', CAST(:query_text AS text))
  LIMIT 100
)
SELECT COALESCE(v.fragrance_id, k.fragrance_id) AS fragrance_id,
       COALESCE(1.0/(:rrf_k + v.rank_v), 0.0)
     + COALESCE(1.0/(:rrf_k + k.rank_f), 0.0) AS rrf_score,
       (v.fragrance_id IS NOT NULL) AS hit_vector,
       (k.fragrance_id IS NOT NULL) AS hit_fts
FROM vector_cte v
FULL OUTER JOIN fts_cte k ON v.fragrance_id = k.fragrance_id
ORDER BY rrf_score DESC, COALESCE(v.fragrance_id, k.fragrance_id) ASC
LIMIT :top_k;
"""
)


_FTS_ONLY_SQL = (
    "WITH "
    + _FILTERED_CTE
    + """,
fts_cte AS (
  SELECT f.id AS fragrance_id,
         ROW_NUMBER() OVER (
           ORDER BY ts_rank_cd(
             to_tsvector('english', f.name || ' ' || coalesce(f.description, '')),
             plainto_tsquery('english', CAST(:query_text AS text))
           ) DESC
         ) AS rank_f
  FROM fragrances f
  JOIN filtered ff ON ff.id = f.id
  WHERE (
    (CAST(:query_text AS text) IS NULL OR CAST(:query_text AS text) = '') OR
    to_tsvector('english', f.name || ' ' || coalesce(f.description, ''))
        @@ plainto_tsquery('english', CAST(:query_text AS text))
  )
  LIMIT 100
)
SELECT k.fragrance_id AS fragrance_id,
       1.0/(:rrf_k + k.rank_f) AS rrf_score,
       FALSE AS hit_vector,
       TRUE AS hit_fts
FROM fts_cte k
ORDER BY rrf_score DESC, k.fragrance_id ASC
LIMIT :top_k;
"""
)


async def _set_ef_search(session: AsyncSession) -> None:
    """ADR-0032: scope HNSW recall tuning to this transaction."""
    await session.execute(text(f"SET LOCAL hnsw.ef_search = {_ef_search_value()}"))


def _build_match_reason(*, hit_vector: bool, hit_fts: bool, ontology: bool) -> list[str]:
    reasons: list[str] = []
    if hit_vector:
        reasons.append("vector")
    if hit_fts:
        reasons.append("fts")
    if ontology:
        reasons.append("ontology")
    return reasons


async def hybrid_retrieve(
    session: AsyncSession,
    *,
    query_embedding: list[float],
    query_text: str,
    filters: FilterSpec,
    top_k: int,
) -> list[RetrievalRow]:
    """Hybrid pgvector + FTS + ontology RRF retrieval. One DB round trip."""
    from .constants import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, EMBEDDING_VIEW

    await _set_ef_search(session)

    params: dict[str, Any] = {
        **_filter_params(filters),
        "query_text": query_text,
        "query_embedding": str(query_embedding),
        "view": EMBEDDING_VIEW,
        "model": EMBEDDING_MODEL,
        "dims": EMBEDDING_DIMENSIONS,
        "rrf_k": RRF_K,
        "top_k": top_k,
    }
    rows = (await session.execute(text(_HYBRID_SQL), params)).all()
    ontology = _ontology_active(filters)

    out: list[RetrievalRow] = []
    for r in rows:
        out.append(
            RetrievalRow(
                fragrance_id=r.fragrance_id,
                relevance_score=_normalize(float(r.rrf_score)),
                match_reason=_build_match_reason(
                    hit_vector=bool(r.hit_vector),
                    hit_fts=bool(r.hit_fts),
                    ontology=ontology,
                ),
            )
        )
    return out


async def fts_retrieve(
    session: AsyncSession,
    *,
    query_text: str,
    filters: FilterSpec,
    top_k: int,
) -> list[RetrievalRow]:
    """FTS + ontology only. Used by the degraded-mode fallback."""
    params: dict[str, Any] = {
        **_filter_params(filters),
        "query_text": query_text,
        "rrf_k": RRF_K,
        "top_k": top_k,
    }
    rows = (await session.execute(text(_FTS_ONLY_SQL), params)).all()
    ontology = _ontology_active(filters)

    out: list[RetrievalRow] = []
    for r in rows:
        out.append(
            RetrievalRow(
                fragrance_id=r.fragrance_id,
                relevance_score=_normalize(float(r.rrf_score)),
                match_reason=_build_match_reason(
                    hit_vector=False,
                    hit_fts=True,
                    ontology=ontology,
                ),
            )
        )
    return out
