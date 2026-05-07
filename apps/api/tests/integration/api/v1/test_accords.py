"""Accords list + detail integration tests."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_list_accords_flat(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/accords")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert len(body["data"]) >= 6
    for a in body["data"]:
        assert "slug" in a and "name" in a


@pytest.mark.asyncio
async def test_accord_detail_paginated_fragrances(
    app_client: httpx.AsyncClient,
) -> None:
    r = await app_client.get("/api/v1/accords/floral?limit=10")
    assert r.status_code == 200
    body = r.json()
    # aventus, no-5, miss-dior = 3
    assert body["fragrances"]["pagination"]["total"] == 3


@pytest.mark.asyncio
async def test_accord_detail_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/accords/no-such")
    assert r.status_code == 404
