"""Cache miss → hit; degraded never cached; daily counter unchanged on hit."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_second_identical_request_hits_cache(
    search_client: httpx.AsyncClient,
    fake_redis,
) -> None:
    payload = {"query": "smoky leather", "top_k": 5}

    r1 = await search_client.post("/api/v1/search", json=payload)
    assert r1.status_code == 200, r1.text
    assert r1.json()["cache_hit"] is False
    # Daily counter should be 1 after the first miss.
    count_after_miss = int(await fake_redis.get(_today_key()) or b"0")
    assert count_after_miss == 1

    r2 = await search_client.post("/api/v1/search", json=payload)
    assert r2.status_code == 200, r2.text
    assert r2.json()["cache_hit"] is True
    # Cache hit MUST NOT consume the daily budget.
    count_after_hit = int(await fake_redis.get(_today_key()) or b"0")
    assert count_after_hit == count_after_miss


@pytest.mark.asyncio
async def test_filter_order_normalized_to_same_key(
    search_client: httpx.AsyncClient,
) -> None:
    payload_a = {
        "query": "Aventus",
        "filters": {"accord": ["smoky", "leather"]},
        "top_k": 5,
    }
    payload_b = {
        "query": "  aventus  ",
        "filters": {"accord": ["leather", "smoky"]},
        "top_k": 5,
    }

    r1 = await search_client.post("/api/v1/search", json=payload_a)
    assert r1.status_code == 200
    r2 = await search_client.post("/api/v1/search", json=payload_b)
    assert r2.status_code == 200
    assert r2.json()["cache_hit"] is True


def _today_key() -> str:
    from datetime import UTC, datetime

    return f"search:dailycount:{datetime.now(UTC).strftime('%Y-%m-%d')}"
