"""Articles list + detail integration tests."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_list_articles(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/articles")
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 1
    a = body["data"][0]
    assert a["slug"] == "top-10-summer"
    assert "title" in a and "published_at" in a


@pytest.mark.asyncio
async def test_article_detail(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/articles/top-10-summer")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "top-10-summer"
    assert body["body"]
    assert body["title"]
    assert isinstance(body["fragrances"], list)


@pytest.mark.asyncio
async def test_article_detail_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/articles/no-such")
    assert r.status_code == 404
