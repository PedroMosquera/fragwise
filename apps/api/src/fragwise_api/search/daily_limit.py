"""Global daily kill-switch for search calls.

Key: `search:dailycount:{YYYY-MM-DD UTC}`. First INCR sets EXPIRE to
seconds-until-next-UTC-midnight + 60 so the counter resets when the day
rolls. Cache hits MUST NOT consume the budget — use `peek_count`.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, time, timedelta

from redis.asyncio import Redis


class DailyLimitReached(RuntimeError):  # noqa: N818
    """Raised when the global daily counter has tripped."""


def daily_limit_value() -> int:
    raw = os.environ.get("FRAGWISE_DAILY_SEARCH_LIMIT", "5000")
    try:
        n = int(raw)
        if n <= 0:
            return 5000
        return n
    except ValueError:
        return 5000


def _day_key(now_utc: datetime) -> str:
    return f"search:dailycount:{now_utc.strftime('%Y-%m-%d')}"


def _seconds_until_next_utc_midnight(now_utc: datetime) -> int:
    next_midnight = datetime.combine((now_utc + timedelta(days=1)).date(), time.min, tzinfo=UTC)
    delta = next_midnight - now_utc
    return max(int(delta.total_seconds()), 1)


async def increment_and_check(r: Redis, limit: int, now_utc: datetime) -> int:
    """INCR the day-key; on the first INCR (TTL < 0), set EXPIRE.

    Raises `DailyLimitReached` when the new count exceeds `limit`.
    """
    key = _day_key(now_utc)
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    new_count, ttl = await pipe.execute()
    new_count = int(new_count)
    if int(ttl) < 0:
        # First INCR of the day: set TTL slightly past midnight to absorb
        # clock skew; -2 means key has no TTL set yet (Redis semantics).
        await r.expire(key, _seconds_until_next_utc_midnight(now_utc) + 60)
    if new_count > limit:
        raise DailyLimitReached()
    return new_count


async def peek_count(r: Redis, now_utc: datetime) -> int:
    """Read the current count without incrementing (cache-hit path)."""
    raw = await r.get(_day_key(now_utc))
    if raw is None:
        return 0
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def is_tripped(r: Redis, limit: int, now_utc: datetime) -> bool:
    """Cache-hit pre-check: returns True iff today's count already > limit."""
    return (await peek_count(r, now_utc)) > limit
