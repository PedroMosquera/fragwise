"""Catalog API v1 — aggregates per-resource routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

# Importing schemas package triggers centralized model_rebuild() (see schemas/__init__.py)
from . import schemas as _schemas  # noqa: F401
from .routers import accords, articles, brands, fragrances, notes, perfumers

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(fragrances.router)
api_router.include_router(brands.router)
api_router.include_router(perfumers.router)
api_router.include_router(notes.router)
api_router.include_router(accords.router)
api_router.include_router(articles.router)

__all__ = ["api_router"]
