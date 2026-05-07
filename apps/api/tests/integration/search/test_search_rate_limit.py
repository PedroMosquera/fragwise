"""Per-IP rate limit returns 429 once the hourly budget is exhausted.

We exercise this by setting the env override to a tiny limit (e.g. 3/hour).
The slowapi limiter uses per-process in-memory storage in tests (see
`make_limiter("memory://")` in conftest), so the counter resets between
tests but persists within a single test.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis as fakeredis_async
import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration


def _embedding(seed: int, dims: int = 512) -> list[float]:
    vec = [0.0] * dims
    vec[seed % dims] = 1.0
    return vec


@pytest_asyncio.fixture()
async def low_rate_client(
    search_engine: AsyncEngine,
    search_seeded: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
    """Build a fresh app with `FRAGWISE_SEARCH_RATE_PER_IP_HOUR=3`."""
    monkeypatch.setenv("FRAGWISE_SEARCH_RATE_PER_IP_HOUR", "3")
    # Rebuild app so per_ip_rate() is read on each request via the limiter
    # decorator inside the route handler.
    from fragwise_api.db.session import make_sessionmaker
    from fragwise_api.main import create_app
    from fragwise_api.search.rate_limit import limiter, set_storage_uri

    set_storage_uri("memory://")
    limiter.reset()

    redis_client = fakeredis_async.FakeRedis()

    openai_client = MagicMock()
    openai_client.close = AsyncMock(return_value=None)
    openai_client.embeddings = MagicMock()

    async def _create(**kwargs: Any) -> Any:
        item = MagicMock()
        item.embedding = _embedding(0)
        resp = MagicMock()
        resp.data = [item]
        return resp

    openai_client.embeddings.create = AsyncMock(side_effect=_create)

    app = create_app()
    app.state.db_engine = search_engine
    app.state.db_sessionmaker = make_sessionmaker(search_engine)
    app.state.redis = redis_client
    app.state.openai_client = openai_client
    app.state.limiter = limiter

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    monkeypatch.delenv("FRAGWISE_SEARCH_RATE_PER_IP_HOUR", raising=False)


@pytest.mark.asyncio
async def test_under_limit_succeeds_then_over_limit_429s(
    low_rate_client: httpx.AsyncClient,
) -> None:
    """3/hour ⇒ requests 1-3 OK, request 4 returns 429."""
    # Use distinct queries so we don't hit the cache (cache hits would not
    # consume the hourly budget here either, but the simplicity helps).
    for i in range(3):
        r = await low_rate_client.post("/api/v1/search", json={"query": f"smoky-{i}", "top_k": 3})
        assert r.status_code == 200, f"req {i + 1}: {r.text}"

    r = await low_rate_client.post("/api/v1/search", json={"query": "smoky-4", "top_k": 3})
    assert r.status_code == 429, r.text
    body = r.json()
    assert body["error"]["code"] == "rate_limited"
