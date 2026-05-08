"""Daily kill-switch: preset `chat:dailycount:<today>=200` -> 503 envelope,
no SSE stream opened (api-app spec: Chat Daily Kill-Switch)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_201st_call_returns_503(
    chat_client: httpx.AsyncClient,
    fake_redis,  # type: ignore[no-untyped-def]
) -> None:
    """Preset today's counter to the cap -> next request increments to 201
    and trips `ChatDailyLimitReached` -> 503 envelope."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    await fake_redis.set(f"chat:dailycount:{today}", "200")

    r = await chat_client.post(
        "/api/v1/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": ("Smoky leather masc winter evening, intensity strong, budget high"),
                }
            ]
        },
    )
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["error"]["code"] == "daily_limit_reached"


@pytest.mark.asyncio
async def test_first_incr_of_day_sets_expire(
    chat_client: httpx.AsyncClient,
    fake_redis,  # type: ignore[no-untyped-def]
) -> None:
    """Per api-app spec: first INCR of a new day MUST set TTL."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"chat:dailycount:{today}"
    assert await fake_redis.get(key) is None

    body = {
        "messages": [
            {
                "role": "user",
                "content": ("Smoky leather masc winter evening, intensity strong, budget high"),
            }
        ]
    }
    async with chat_client.stream("POST", "/api/v1/chat", json=body) as resp:
        assert resp.status_code == 200
        await resp.aread()

    raw = await fake_redis.get(key)
    assert raw is not None
    assert int(raw) == 1
    ttl = await fake_redis.ttl(key)
    assert ttl > 0, "first INCR of the day MUST set EXPIRE"
