"""Chat daily kill-switch — Redis INCR + EXPIRE.

Mirrors `search/daily_limit.py` verbatim under the `chat:dailycount:`
namespace. Independent budget — chat fans out to 3-5 LLM calls per turn
so the cap is tighter (200/day default vs search's 5000/day).

Per api-app spec "Chat Daily Kill-Switch": first INCR of a new UTC day
sets EXPIRE to (next UTC midnight) + 60s buffer. 503 is reserved for this
counter — OpenAI outages MUST NOT produce 503.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, time, timedelta

from redis.asyncio import Redis

from .constants import DAILY_CAP_DEFAULT


class ChatDailyLimitReached(RuntimeError):  # noqa: N818
    """Raised when the chat global daily counter has tripped."""


def chat_daily_limit_value() -> int:
    """Read `FRAGWISE_DAILY_CHAT_LIMIT`, defaulting to `DAILY_CAP_DEFAULT`."""
    raw = os.environ.get("FRAGWISE_DAILY_CHAT_LIMIT", str(DAILY_CAP_DEFAULT))
    try:
        n = int(raw)
        if n <= 0:
            return DAILY_CAP_DEFAULT
        return n
    except ValueError:
        return DAILY_CAP_DEFAULT


def _day_key(now_utc: datetime) -> str:
    """Build today's key under the chat namespace."""
    return f"chat:dailycount:{now_utc.strftime('%Y-%m-%d')}"


def _seconds_until_next_utc_midnight(now_utc: datetime) -> int:
    """Whole-second countdown to the next UTC midnight (>=1)."""
    next_midnight = datetime.combine(
        (now_utc + timedelta(days=1)).date(),
        time.min,
        tzinfo=UTC,
    )
    delta = next_midnight - now_utc
    return max(int(delta.total_seconds()), 1)


async def chat_increment_and_check(
    r: Redis,
    limit: int,
    now_utc: datetime,
) -> int:
    """INCR the day-key; on the first INCR (TTL < 0), set EXPIRE.

    Raises `ChatDailyLimitReached` when the new count exceeds `limit`.
    """
    key = _day_key(now_utc)
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    new_count, ttl = await pipe.execute()
    new_count = int(new_count)
    if int(ttl) < 0:
        await r.expire(key, _seconds_until_next_utc_midnight(now_utc) + 60)
    if new_count > limit:
        raise ChatDailyLimitReached()
    return new_count
