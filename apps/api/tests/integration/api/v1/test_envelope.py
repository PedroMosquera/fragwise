"""Envelope + middleware behavior: error shape, redirect_slashes, CORS."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_list_envelope_shape(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?limit=2")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"data", "pagination"}
    assert set(body["pagination"].keys()) == {"limit", "offset", "total", "has_next"}


@pytest.mark.asyncio
async def test_error_envelope_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/brands/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert set(body["error"].keys()) >= {"code", "message"}
    assert body["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_error_envelope_422(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?year_min=abc")
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "invalid_params"
    # W7: input/ctx must NOT leak through.
    detail = body["error"]["detail"]
    if isinstance(detail, list):
        for item in detail:
            assert "input" not in item
            assert "ctx" not in item


@pytest.mark.asyncio
async def test_trailing_slash_returns_404_not_307(
    app_client: httpx.AsyncClient,
) -> None:
    r = await app_client.get("/api/v1/fragrances/", follow_redirects=False)
    assert r.status_code == 404
    assert "location" not in {k.lower() for k in r.headers}


@pytest.mark.asyncio
async def test_unversioned_route_is_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/fragrances")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_health_probes_unversioned(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_cors_preflight_allows_origin(
    app_client: httpx.AsyncClient,
) -> None:
    """F6: preflight succeeds and never echoes `*` with credentials."""
    r = await app_client.options(
        "/api/v1/fragrances",
        headers={
            "Origin": "https://fragwise.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code in (200, 204)
    # allow_credentials=False; header MUST NOT be 'true'
    creds = r.headers.get("access-control-allow-credentials")
    assert creds is None or creds.lower() == "false"
