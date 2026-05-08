"""Rate-limit per-IP: 5/h + 20/d. 6th request in an hour -> 429 envelope,
no SSE stream opened (api-app spec: Chat Rate Limiting)."""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _shrink_hour_window(monkeypatch: pytest.MonkeyPatch) -> None:
    # Defaults: 5/hour. Keep them.
    monkeypatch.setenv("FRAGWISE_CHAT_RATE_PER_IP_HOUR", "5")
    monkeypatch.setenv("FRAGWISE_CHAT_RATE_PER_IP_DAY", "20")
    # Reset env for cleanliness.
    yield
    os.environ.pop("FRAGWISE_CHAT_RATE_PER_IP_HOUR", None)
    os.environ.pop("FRAGWISE_CHAT_RATE_PER_IP_DAY", None)


@pytest.mark.asyncio
async def test_sixth_hourly_request_returns_429(
    chat_client: httpx.AsyncClient,
) -> None:
    body = {
        "messages": [
            {
                "role": "user",
                "content": ("Smoky leather masc winter evening, intensity strong, budget high"),
            }
        ]
    }
    # Drain 5 successful turns (can be SSE 200; we don't read the stream).
    for _ in range(5):
        async with chat_client.stream("POST", "/api/v1/chat", json=body) as resp:
            assert resp.status_code == 200
            await resp.aread()
    # 6th request must trip the per-IP hour window.
    r = await chat_client.post("/api/v1/chat", json=body)
    assert r.status_code == 429, r.text
    payload = r.json()
    assert payload["error"]["code"] == "rate_limited"
