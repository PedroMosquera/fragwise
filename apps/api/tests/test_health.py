"""Smoke test for /healthz."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_healthz_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")
