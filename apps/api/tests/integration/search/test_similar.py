"""POST /api/v1/fragrances/{slug}/similar — no OpenAI call, slug + embedding 404s."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_similar_returns_results_without_openai(
    search_client: httpx.AsyncClient,
    fake_openai,
) -> None:
    r = await search_client.post("/api/v1/fragrances/aventus/similar", json={"top_k": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body and "degraded" in body and "cache_hit" in body
    assert body["degraded"] is False
    # OpenAI MUST NOT be invoked: similar uses the stored embedding.
    fake_openai.embeddings.create.assert_not_called()
    # The source fragrance should not appear in its own similars list.
    slugs = [hit["fragrance"]["slug"] for hit in body["data"]]
    assert "aventus" not in slugs


@pytest.mark.asyncio
async def test_unknown_slug_returns_404(
    search_client: httpx.AsyncClient,
) -> None:
    r = await search_client.post("/api/v1/fragrances/does-not-exist/similar", json={"top_k": 5})
    assert r.status_code == 404, r.text
    body = r.json()
    assert body["error"]["code"] == "not_found"
    assert "does-not-exist" in body["error"]["message"]


@pytest.mark.asyncio
async def test_missing_embedding_returns_404(
    search_client: httpx.AsyncClient,
) -> None:
    """`legacy` exists but has no row in `fragrance_embeddings`."""
    r = await search_client.post("/api/v1/fragrances/legacy/similar", json={"top_k": 5})
    assert r.status_code == 404, r.text
    body = r.json()
    assert body["error"]["code"] == "not_found"
    assert "embedding" in body["error"]["message"]
