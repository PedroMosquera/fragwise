"""Brand list + detail integration tests; F5 ILIKE-escape edges."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_list_brands(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/brands")
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 3
    slugs = [b["slug"] for b in body["data"]]
    assert slugs == sorted(slugs)


@pytest.mark.asyncio
async def test_brands_q_substring(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/brands?q=ch")
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["slug"] == "chanel"


@pytest.mark.asyncio
@pytest.mark.parametrize("q", ["%", "_", "foo\\bar", "50%"])
async def test_brands_q_ilike_escape_zero_rows(app_client: httpx.AsyncClient, q: str) -> None:
    """F5: glob-meta and backslash inputs MUST not match every row.

    None of the seeded brand names (`Chanel`, `Dior`, `Creed`) literally
    contains these characters, so a correctly-escaped ILIKE returns zero.
    """
    r = await app_client.get("/api/v1/brands", params={"q": q})
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_brand_detail_paginated_fragrances(
    app_client: httpx.AsyncClient,
) -> None:
    r = await app_client.get("/api/v1/brands/chanel?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "chanel"
    assert body["fragrances"]["pagination"]["total"] == 2  # no-5 + miss-dior
    assert len(body["fragrances"]["data"]) == 2


@pytest.mark.asyncio
async def test_brand_detail_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/brands/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
