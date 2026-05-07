"""slowapi limiter for `/api/v1/search` and `/api/v1/fragrances/{slug}/similar`.

Per-IP `60/hour` is the default; operators override via
`FRAGWISE_SEARCH_RATE_PER_IP_HOUR`. The limiter is a module-level singleton
because slowapi's FastAPI integration needs the decorator applied at route
definition time. `make_limiter` is still exposed so `main.lifespan` can
reconfigure the storage backend (e.g. memory:// in tests).

The 429 envelope MUST match `{"error": {"code": "rate_limited", "message": "..."}}`
per the spec; `rate_limit_exceeded_handler` produces that body.
"""

from __future__ import annotations

import contextlib
import os
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def per_ip_rate() -> str:
    """Read the per-IP hourly budget from env, defaulting to 60/hour."""
    raw = os.environ.get("FRAGWISE_SEARCH_RATE_PER_IP_HOUR", "60")
    try:
        n = int(raw)
        if n <= 0:
            n = 60
    except ValueError:
        n = 60
    return f"{n}/hour"


def make_limiter(redis_url: str) -> Limiter:
    """Build a Limiter backed by Redis (or any limits-supported URI).

    headers_enabled=False: with the decorator approach, slowapi tries to
    inject X-RateLimit-* headers BEFORE FastAPI converts the route's
    return value into a Response. Disabling avoids the type assertion
    inside _inject_headers. We can re-enable later by mounting
    SlowAPIMiddleware if operators want the headers exposed.
    """
    return Limiter(
        key_func=get_remote_address,
        storage_uri=redis_url,
        headers_enabled=False,
        in_memory_fallback_enabled=True,
        swallow_errors=True,
    )


# Module-level limiter — required because slowapi's FastAPI integration
# applies the rate-limit decorator at route definition time. Lifespan
# rebinds storage via `set_storage_uri()` so the same limiter object can
# point at Redis in prod and `memory://` in tests.
limiter: Limiter = make_limiter(os.environ.get("REDIS_URL", "memory://"))


def set_storage_uri(redis_url: str) -> None:
    """Rebuild the storage backend for the module-level limiter.

    slowapi has no public setter, so we replace the underlying storage on
    the existing `limits.aio.strategies` object via the public `Limiter`
    API. Simplest stable approach: rebuild the `limits` storage by calling
    the Limiter's __init__-equivalent helpers exposed on the instance.
    """
    new_limiter = make_limiter(redis_url)
    # Copy the new internal state onto the singleton so already-decorated
    # routes keep working after lifespan reconfigures the URL.
    limiter._storage_uri = redis_url
    limiter._storage = new_limiter._storage
    limiter._limiter = new_limiter._limiter


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Replace slowapi's default plain-text 429 with our error envelope."""
    assert isinstance(exc, RateLimitExceeded)
    body: dict[str, Any] = {
        "error": {
            "code": "rate_limited",
            "message": f"rate limit exceeded: {exc.detail}",
            "detail": None,
        }
    }
    response = JSONResponse(status_code=429, content=body)
    # Preserve slowapi's RateLimit-* headers when available.
    with contextlib.suppress(AttributeError, KeyError, Exception):
        limiter._inject_headers(response, request.state.view_rate_limit)
    return response
