"""Chat degraded-mode fallback (api-app spec: Chat Degraded-Mode Fallback).

Three scenarios:
  1. Intake failure -> `degraded(openai_intake_failed)`, generic clarify
     follows, response is 200 (NEVER 503 from OpenAI outage).
  2. Embedding failure -> `degraded(openai_embedding_failed)`, FTS path
     taken, pipeline continues, `done(complete)`.
  3. Explain failure -> `degraded(openai_explain_failed)`, no
     `recommendation` events, `done(degraded)`, response is 200.
"""

from __future__ import annotations

import httpx
import pytest

from .conftest import StubAsyncOpenAI, StubScript, _make_chat_app, consume_sse

pytestmark = pytest.mark.integration


async def _run(chat_engine, chat_seeded, fake_redis, script: StubScript):  # type: ignore[no-untyped-def]
    stub = StubAsyncOpenAI(script)
    app = _make_chat_app(chat_engine, fake_redis, stub)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await consume_sse(
            client,
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Smoky leather masc winter evening, intensity strong, budget high"
                        ),
                    }
                ]
            },
        )


@pytest.mark.asyncio
async def test_intake_failure_degrades_then_clarifies(
    chat_engine,
    chat_seeded,
    fake_redis,  # type: ignore[no-untyped-def]
) -> None:
    status, events, _ = await _run(
        chat_engine,
        chat_seeded,
        fake_redis,
        StubScript(intake_raises=True),
    )
    # NEVER 503 from OpenAI outage.
    assert status == 200
    degraded = [e for e in events if e.event == "degraded"]
    assert any(d.data.get("reason") == "openai_intake_failed" for d in degraded)
    # A clarify event MUST follow as the generic fallback.
    assert any(e.event == "clarify" for e in events)
    assert events[-1].event == "done"
    assert events[-1].data["finish_reason"] == "degraded"


@pytest.mark.asyncio
async def test_embedding_failure_falls_through_to_fts(
    chat_engine,
    chat_seeded,
    fake_redis,  # type: ignore[no-untyped-def]
) -> None:
    """FTS plainto_tsquery uses AND semantics; build a query whose tokens
    all appear in the seeded description "smoky woody bergamot" (sauvage)
    so the FTS branch returns at least one row even without the embedding
    round-trip. Clarify gates on `gender + occasion + season + intensity +
    budget`; we populate all five with terms that either match the FTS
    text or are short enough not to collapse the AND."""
    script = StubScript(
        embed_raises=True,
        intake_prefs={
            "gender": "masculine",
            "occasion": "smoky",
            "season": "smoky",
            "intensity": "smoky",
            "families": ["smoky"],
            "budget": "high",
        },
    )
    status, events, _ = await _run(chat_engine, chat_seeded, fake_redis, script)
    assert status == 200
    degraded = [e for e in events if e.event == "degraded"]
    assert any(d.data.get("reason") == "openai_embedding_failed" for d in degraded)
    # Rank + explain still ran -> `done(complete)`.
    assert events[-1].event == "done"
    assert events[-1].data["finish_reason"] == "complete"


@pytest.mark.asyncio
async def test_explain_failure_emits_degraded_then_done_degraded(
    chat_engine,
    chat_seeded,
    fake_redis,  # type: ignore[no-untyped-def]
) -> None:
    status, events, _ = await _run(
        chat_engine,
        chat_seeded,
        fake_redis,
        StubScript(explain_raises=True),
    )
    assert status == 200
    degraded = [e for e in events if e.event == "degraded"]
    assert any(d.data.get("reason") == "openai_explain_failed" for d in degraded)
    rec = [e for e in events if e.event == "recommendation"]
    assert rec == []
    assert events[-1].event == "done"
    assert events[-1].data["finish_reason"] == "degraded"


@pytest.mark.asyncio
async def test_503_reserved_for_daily_kill_switch_only(
    chat_engine,
    chat_seeded,
    fake_redis,  # type: ignore[no-untyped-def]
) -> None:
    """All OpenAI nodes fail -> still 200 (degraded), NEVER 503."""
    status, _events, _ = await _run(
        chat_engine,
        chat_seeded,
        fake_redis,
        StubScript(intake_raises=True, rank_raises=True, explain_raises=True),
    )
    assert status == 200, "OpenAI outages MUST NEVER produce 503"
