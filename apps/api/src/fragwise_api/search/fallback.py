"""FTS + ontology fallback used when OpenAI embedding fails.

ADR-0029: never 503 for OpenAI outages — the daily kill-switch owns 503.
The handler tags the response with `degraded=True` and skips the cache
write so a transient OpenAI hiccup doesn't poison the cache for 24h.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .retrieval import RetrievalRow, fts_retrieve
from .schemas import FilterSpec


async def fts_only_retrieval(
    session: AsyncSession,
    *,
    query_text: str,
    filters: FilterSpec,
    top_k: int,
) -> list[RetrievalRow]:
    """Pure FTS + ontology path. Same filter pushdown as hybrid."""
    return await fts_retrieve(
        session,
        query_text=query_text,
        filters=filters,
        top_k=top_k,
    )
