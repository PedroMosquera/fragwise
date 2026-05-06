"""Pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from fragwise_api.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
