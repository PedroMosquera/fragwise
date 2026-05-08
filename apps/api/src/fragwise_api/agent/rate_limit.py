"""slowapi limiter for `POST /api/v1/chat`. Multi-window: 5/h AND 20/d.

slowapi semantics: when multiple `@chat_limiter.limit(...)` decorators stack
on one route, EACH window is enforced independently — the request is
rejected when ANY window's threshold is exceeded (path "a" from design
note; verified via Context7).

Mirrors `search/rate_limit.py`: a module-level `Limiter` is required because
slowapi's FastAPI integration wraps the route at decoration time. Lifespan
rebinds storage via `set_chat_storage_uri()` so the same singleton can
point at Redis in prod and `memory://` in tests.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from .constants import PER_IP_DAY, PER_IP_HOUR


def per_ip_hour() -> str:
    """Hourly per-IP budget. Env override wins; bad values fall back."""
    raw = os.environ.get("FRAGWISE_CHAT_RATE_PER_IP_HOUR", str(PER_IP_HOUR))
    try:
        n = int(raw)
        if n <= 0:
            n = PER_IP_HOUR
    except ValueError:
        n = PER_IP_HOUR
    return f"{n}/hour"


def per_ip_day() -> str:
    """Daily per-IP budget. Env override wins; bad values fall back."""
    raw = os.environ.get("FRAGWISE_CHAT_RATE_PER_IP_DAY", str(PER_IP_DAY))
    try:
        n = int(raw)
        if n <= 0:
            n = PER_IP_DAY
    except ValueError:
        n = PER_IP_DAY
    return f"{n}/day"


def make_chat_limiter(redis_url: str) -> Limiter:
    """Build a chat-specific Limiter with the same operational tuning as
    `search/rate_limit.py::make_limiter` (headers disabled, in-memory
    fallback enabled, errors swallowed)."""
    return Limiter(
        key_func=get_remote_address,
        storage_uri=redis_url,
        headers_enabled=False,
        in_memory_fallback_enabled=True,
        swallow_errors=True,
    )


# Module-level singleton — required because slowapi's FastAPI integration
# applies the rate-limit decorator at route definition time. Lifespan
# rebinds storage via `set_chat_storage_uri()`.
chat_limiter: Limiter = make_chat_limiter(os.environ.get("REDIS_URL", "memory://"))


def set_chat_storage_uri(redis_url: str) -> None:
    """Rebuild the storage backend for the module-level chat limiter.

    Mirrors `search/rate_limit.py::set_storage_uri` verbatim — replaces the
    underlying storage on the existing `Limiter` instance so already-decorated
    routes pick up the new URL after lifespan boots Redis.
    """
    new_limiter = make_chat_limiter(redis_url)
    chat_limiter._storage_uri = redis_url
    chat_limiter._storage = new_limiter._storage
    chat_limiter._limiter = new_limiter._limiter
