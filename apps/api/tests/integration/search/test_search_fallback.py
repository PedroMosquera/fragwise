"""OpenAI failure → 200 + degraded=true + FTS-only path; not cached."""

from __future__ import annotations

import httpx
import pytest
from openai import APIConnectionError

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_openai_connection_error_degrades(
    search_client: httpx.AsyncClient,
    fake_openai,
) -> None:
    # Simulate persistent OpenAI failure on every retry attempt.
    async def _fail(**kwargs):
        raise APIConnectionError(request=None)  # type: ignore[arg-type]

    fake_openai.embeddings.create.side_effect = _fail

    r = await search_client.post("/api/v1/search", json={"query": "smoky", "top_k": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["degraded"] is True
    assert body["cache_hit"] is False
    # Every match_reason must come from FTS (no vector signal in degraded mode).
    for hit in body["data"]:
        assert "vector" not in hit["match_reason"]


@pytest.mark.asyncio
async def test_degraded_response_not_cached(
    search_client: httpx.AsyncClient,
    fake_openai,
    fake_redis,
) -> None:
    async def _fail(**kwargs):
        raise APIConnectionError(request=None)  # type: ignore[arg-type]

    fake_openai.embeddings.create.side_effect = _fail

    r1 = await search_client.post("/api/v1/search", json={"query": "smoky", "top_k": 5})
    assert r1.status_code == 200
    assert r1.json()["degraded"] is True

    # No `search:v1:*` key was written.
    keys = [k async for k in fake_redis.scan_iter(match="search:v1:*")]
    assert keys == []
