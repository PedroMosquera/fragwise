"""Daily kill-switch INCR + EXPIRE-on-first-INCR semantics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import fakeredis.aioredis as fakeredis_async
import pytest

from fragwise_api.search.daily_limit import (
    DailyLimitReached,
    increment_and_check,
    is_tripped,
    peek_count,
)


@pytest.mark.asyncio
async def test_increment_and_check_sets_expire_on_first_incr() -> None:
    r = fakeredis_async.FakeRedis()
    now = datetime.now(UTC)

    n = await increment_and_check(r, limit=10, now_utc=now)
    assert n == 1
    key = f"search:dailycount:{now.strftime('%Y-%m-%d')}"
    ttl = await r.ttl(key)
    # On a fresh key the EXPIRE should be set to seconds-until-midnight + 60.
    assert ttl > 0
    assert ttl <= 24 * 3600 + 120  # generous upper bound


@pytest.mark.asyncio
async def test_peek_count_does_not_increment() -> None:
    r = fakeredis_async.FakeRedis()
    now = datetime.now(UTC)
    await increment_and_check(r, limit=10, now_utc=now)
    before = await peek_count(r, now)
    again = await peek_count(r, now)
    assert before == again == 1


@pytest.mark.asyncio
async def test_increment_raises_when_over_limit() -> None:
    r = fakeredis_async.FakeRedis()
    now = datetime.now(UTC)
    for _ in range(3):
        await increment_and_check(r, limit=3, now_utc=now)
    with pytest.raises(DailyLimitReached):
        await increment_and_check(r, limit=3, now_utc=now)


@pytest.mark.asyncio
async def test_is_tripped_reflects_current_count() -> None:
    r = fakeredis_async.FakeRedis()
    now = datetime.now(UTC)
    assert (await is_tripped(r, limit=2, now_utc=now)) is False
    await increment_and_check(r, limit=10, now_utc=now)
    await increment_and_check(r, limit=10, now_utc=now)
    await increment_and_check(r, limit=10, now_utc=now)
    assert (await is_tripped(r, limit=2, now_utc=now)) is True


@pytest.mark.asyncio
async def test_day_rollover_starts_fresh_key() -> None:
    r = fakeredis_async.FakeRedis()
    today = datetime(2026, 5, 7, 23, 0, tzinfo=UTC)
    tomorrow = today + timedelta(days=1)
    for _ in range(5):
        await increment_and_check(r, limit=10, now_utc=today)
    assert await peek_count(r, today) == 5
    # New UTC day → new key starts at 0
    assert await peek_count(r, tomorrow) == 0
    n = await increment_and_check(r, limit=10, now_utc=tomorrow)
    assert n == 1
