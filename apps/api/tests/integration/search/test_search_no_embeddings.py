"""Catalog with zero embedding rows still returns FTS + ontology results.

This exercises the hybrid SQL path when the vector CTE returns 0 rows. The
FULL OUTER JOIN with FTS still produces a result set; the response must
have at least one match_reason of `fts`/`ontology` and no `vector`.
"""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_catalog_without_embeddings_returns_fts_results(
    search_client: httpx.AsyncClient,
    search_engine: AsyncEngine,
) -> None:
    # Wipe embeddings only; leave fragrances + ontology intact.
    sm = async_sessionmaker(search_engine, expire_on_commit=False)
    async with sm() as session:
        await session.execute(text("DELETE FROM fragrance_embeddings"))
        await session.commit()

    r = await search_client.post("/api/v1/search", json={"query": "smoky", "top_k": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["degraded"] is False  # OpenAI succeeded; just no vector hits
    # FTS-only matches should still be in the result set.
    for hit in body["data"]:
        assert "vector" not in hit["match_reason"]
        assert "fts" in hit["match_reason"] or "ontology" in hit["match_reason"]
