"""Fragrance list + detail integration tests."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_list_fragrances_envelope(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body and "pagination" in body
    p = body["pagination"]
    assert isinstance(p["limit"], int)
    assert isinstance(p["offset"], int)
    assert isinstance(p["total"], int)
    assert isinstance(p["has_next"], bool)
    assert p["total"] == 5  # seeded
    assert len(body["data"]) == 5
    # Stable name-asc ordering: Aventus, Homme, Miss Dior, No 5, Sauvage
    names = [item["name"] for item in body["data"]]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_pagination_offset_beyond_total(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?offset=100&limit=20")
    assert r.status_code == 200
    body = r.json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 5
    assert body["pagination"]["has_next"] is False


@pytest.mark.asyncio
async def test_invalid_limit_422(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?limit=500")
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "invalid_params"


@pytest.mark.asyncio
async def test_negative_offset_422(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?offset=-1")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_brand_and_gender_filter(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?brand=chanel&gender=fem")
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 2  # no-5, miss-dior
    for item in body["data"]:
        assert item["brand"]["slug"] == "chanel"
        assert item["gender"] == "fem"


@pytest.mark.asyncio
async def test_multi_value_accord_or(app_client: httpx.AsyncClient) -> None:
    """Repeated `?accord=` keys OR within. floral OR woody returns all 5."""
    r = await app_client.get("/api/v1/fragrances?accord=floral&accord=woody")
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 5


@pytest.mark.asyncio
async def test_multi_value_note_or(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?note=jasmine&note=rose")
    assert r.status_code == 200
    body = r.json()
    # aventus (jasmine top + rose heart), no-5 (jasmine), miss-dior (rose) = 3
    assert body["pagination"]["total"] == 3


@pytest.mark.asyncio
async def test_year_range_filter(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances?year_min=2010&year_max=2015")
    assert r.status_code == 200
    body = r.json()
    # aventus 2010, homme 2011, sauvage 2015 = 3
    assert body["pagination"]["total"] == 3


@pytest.mark.asyncio
async def test_detail_happy_path(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances/aventus")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "aventus"
    assert body["brand"]["slug"] == "creed"
    assert isinstance(body["perfumers"], list)
    assert "top" in body["notes"] and "heart" in body["notes"] and "base" in body["notes"]
    assert any(n["slug"] == "jasmine" for n in body["notes"]["top"])
    assert any(n["slug"] == "rose" for n in body["notes"]["heart"])
    assert any(n["slug"] == "vanilla" for n in body["notes"]["base"])
    assert any(a["slug"] == "floral" for a in body["accords"])
    assert isinstance(body["articles"], list)


@pytest.mark.asyncio
async def test_detail_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/fragrances/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_detail_query_count_bounded(
    app_client: httpx.AsyncClient,
    query_counter: dict[str, int],
) -> None:
    """Spec: detail issues <= 6 SELECTs."""
    query_counter["selects"] = 0
    r = await app_client.get("/api/v1/fragrances/aventus")
    assert r.status_code == 200
    assert query_counter["selects"] <= 6, f"selects={query_counter['selects']}"
