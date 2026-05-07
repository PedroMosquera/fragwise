"""Notes tree + detail integration tests; depth-2 assertion."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_notes_tree_depth2(app_client: httpx.AsyncClient) -> None:
    """Tree must surface citrus → bergamot → bergamot-mint (depth-2)."""
    r = await app_client.get("/api/v1/notes")
    assert r.status_code == 200
    data = r.json()["data"]
    citrus = next((n for n in data if n["slug"] == "citrus"), None)
    assert citrus is not None, "citrus root not present"
    bergamot = next((c for c in citrus["children"] if c["slug"] == "bergamot"), None)
    assert bergamot is not None, "bergamot child not present"
    grandchild = next(
        (c for c in bergamot["children"] if c["slug"] == "bergamot-mint"),
        None,
    )
    assert grandchild is not None, "depth-2 descendant missing"


@pytest.mark.asyncio
async def test_note_detail_with_parent(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/notes/bergamot")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "bergamot"
    assert body["parent"] is not None
    assert body["parent"]["slug"] == "citrus"


@pytest.mark.asyncio
async def test_note_detail_root_has_no_parent(
    app_client: httpx.AsyncClient,
) -> None:
    r = await app_client.get("/api/v1/notes/citrus")
    assert r.status_code == 200
    assert r.json()["parent"] is None


@pytest.mark.asyncio
async def test_note_detail_404(app_client: httpx.AsyncClient) -> None:
    r = await app_client.get("/api/v1/notes/no-such")
    assert r.status_code == 404
