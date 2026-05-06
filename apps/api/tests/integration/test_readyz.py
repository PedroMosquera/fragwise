"""/readyz: 200 (DB up) and 503 (DB unreachable) via ASGI transport."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[2]


def _cfg(url: str) -> Config:
    os.environ["DATABASE_URL"] = url
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    return cfg


@pytest.mark.asyncio
async def test_readyz_up(database_url: str) -> None:
    import asyncio as _asyncio

    await _asyncio.to_thread(command.upgrade, _cfg(database_url), "head")
    # Ensure the env var is set for create_app's lifespan.
    os.environ["DATABASE_URL"] = database_url
    from fragwise_api.main import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://t") as c,
        app.router.lifespan_context(app),
    ):
        r = await c.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_readyz_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://fragwise:fragwise@127.0.0.1:1/none",
    )
    from fragwise_api.main import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://t") as c,
        app.router.lifespan_context(app),
    ):
        r = await c.get("/readyz")
    assert r.status_code == 503
    assert r.json()["status"] == "unready"
