"""POST /api/v1/search — happy path."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_hybrid_search_returns_ranked_candidates(
    search_client: httpx.AsyncClient,
) -> None:
    r = await search_client.post(
        "/api/v1/search",
        json={"query": "smoky leather", "top_k": 5},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["degraded"] is False
    assert body["cache_hit"] is False
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) <= 5
    assert len(body["data"]) > 0

    # Every candidate has a non-empty match_reason in the closed taxonomy
    # and a relevance_score within [0, 1]; results are descending by score.
    last_score = float("inf")
    for hit in body["data"]:
        assert 0.0 <= hit["relevance_score"] <= 1.0
        assert hit["match_reason"]
        assert all(r in {"vector", "fts", "ontology"} for r in hit["match_reason"])
        # FragranceListItem-shape check
        f = hit["fragrance"]
        assert "id" in f and "slug" in f and "name" in f
        assert "brand" in f
        assert hit["relevance_score"] <= last_score
        last_score = hit["relevance_score"]


@pytest.mark.asyncio
async def test_invalid_request_returns_422(
    search_client: httpx.AsyncClient,
) -> None:
    r = await search_client.post("/api/v1/search", json={"query": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "invalid_params"

    r = await search_client.post("/api/v1/search", json={"query": "x", "top_k": 999})
    assert r.status_code == 422
