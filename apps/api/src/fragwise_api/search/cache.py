"""Exact-match Redis cache for `POST /api/v1/search`.

Key: `search:v1:{sha256(normalized_request_json)}`. Normalization rules
mirror the spec: query is lowercased+stripped, filter dict keys sorted,
filter list values sorted, top_k included as int, include sorted.
ADR-0028: only exact-match cache; semantic cache deferred until we have
hit-rate telemetry.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from redis.asyncio import Redis

from .constants import CACHE_NAMESPACE, CACHE_TTL_SECONDS
from .schemas import SearchRequest


def _normalize(req: SearchRequest) -> dict[str, Any]:
    return {
        "query": req.query.strip().lower(),
        "filters": {
            "gender": req.filters.gender,
            "accord": sorted(req.filters.accord),
            "brand": req.filters.brand,
            "year_min": req.filters.year_min,
            "year_max": req.filters.year_max,
            "concentration": req.filters.concentration,
            "note": sorted(req.filters.note),
        },
        "top_k": req.top_k,
        "include": sorted(req.include),
    }


def cache_key(req: SearchRequest) -> str:
    """SHA256 over the canonical-JSON-serialized normalized request."""
    payload = json.dumps(_normalize(req), sort_keys=True, separators=(",", ":"))
    digest = sha256(payload.encode("utf-8")).hexdigest()
    return f"{CACHE_NAMESPACE}:{digest}"


async def get_cached(redis: Redis, key: str) -> dict[str, Any] | None:
    """Return the decoded JSON body, or None on miss / decode error."""
    raw = await redis.get(key)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
        return None
    except json.JSONDecodeError:
        return None


async def set_cached(
    redis: Redis,
    key: str,
    value: dict[str, Any],
    ttl: int = CACHE_TTL_SECONDS,
) -> None:
    """Write the response payload as JSON with the configured TTL."""
    payload = json.dumps(value, separators=(",", ":"), default=str)
    await redis.set(key, payload, ex=ttl)
