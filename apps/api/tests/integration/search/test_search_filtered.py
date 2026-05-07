"""Filter pushdown invariant: filters apply as SQL predicates, not Python post-filtering."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_filter_excludes_top_vector_match(
    search_client: httpx.AsyncClient,
) -> None:
    """Spec scenario: filter excludes the otherwise-top vector match.

    In the seeded fixture, 'aventus' is masc, embedding-rank #1. When
    filter `gender=feminine` is applied, the response MUST NOT contain
    aventus, and the top result must be one of the feminine fragrances
    (no-5 or miss-dior).
    """
    r = await search_client.post(
        "/api/v1/search",
        json={
            "query": "smoky leather",
            "filters": {"gender": "feminine"},
            "top_k": 5,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    slugs = [hit["fragrance"]["slug"] for hit in body["data"]]
    assert "aventus" not in slugs
    assert "sauvage" not in slugs
    assert all(slug in {"no-5", "miss-dior"} for slug in slugs)
    # Ontology tag is added because gender filter is active.
    for hit in body["data"]:
        assert "ontology" in hit["match_reason"]


@pytest.mark.asyncio
async def test_brand_filter_pushdown(
    search_client: httpx.AsyncClient,
) -> None:
    r = await search_client.post(
        "/api/v1/search",
        json={
            "query": "perfume",
            "filters": {"brand": "creed"},
            "top_k": 10,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    for hit in body["data"]:
        assert hit["fragrance"]["brand"]["slug"] == "creed"


@pytest.mark.asyncio
async def test_accord_filter_pushdown(
    search_client: httpx.AsyncClient,
) -> None:
    r = await search_client.post(
        "/api/v1/search",
        json={
            "query": "fragrance",
            "filters": {"accord": ["floral"]},
            "top_k": 10,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    slugs = {hit["fragrance"]["slug"] for hit in body["data"]}
    # Only no-5 and miss-dior have the floral accord
    assert slugs.issubset({"no-5", "miss-dior"})
