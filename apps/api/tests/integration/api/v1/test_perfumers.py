"""Perfumer list + detail integration tests."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_list_perfumers(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/perfumers")
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 2


@pytest.mark.asyncio
async def test_perfumers_q_filter(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/perfumers?q=jean")
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["slug"] == "jean-claude-ellena"


@pytest.mark.asyncio
@pytest.mark.parametrize("q", ["%", "_", "foo\\bar"])
async def test_perfumers_q_ilike_escape(app_client: httpx.AsyncClient, q: str) -> None:
    r = await app_client.get("/api/v1/perfumers", params={"q": q})
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_perfumer_detail(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/perfumers/francis-kurkdjian")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "francis-kurkdjian"
    # aventus + sauvage = 2
    assert body["fragrances"]["pagination"]["total"] == 2


@pytest.mark.asyncio
async def test_perfumer_detail_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/perfumers/does-not-exist")
    assert r.status_code == 404
