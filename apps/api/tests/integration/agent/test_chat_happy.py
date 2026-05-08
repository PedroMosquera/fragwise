"""POST /api/v1/chat — happy path SSE stream.

Exercises the agent spec scenario "Happy-path stream terminates with
done(complete)" using the stubbed AsyncOpenAI client.
"""

from __future__ import annotations

import httpx
import pytest

from .conftest import consume_sse

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_happy_path_completes_with_done_complete(
    chat_client: httpx.AsyncClient,
) -> None:
    status, events, err = await consume_sse(
        chat_client,
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Looking for a smoky leather masc winter evening "
                        "fragrance, intensity strong, budget high"
                    ),
                }
            ]
        },
    )
    assert status == 200, err
    assert events, "expected at least one SSE event"
    # `done` is always last and reports `complete` for happy paths.
    assert events[-1].event == "done"
    assert events[-1].data["finish_reason"] == "complete"
    rec_events = [e for e in events if e.event == "recommendation"]
    assert rec_events, "expected at least one recommendation event"
    for ev in rec_events:
        f = ev.data["fragrance"]
        assert "slug" in f and "name" in f and "brand_slug" in f
        assert isinstance(ev.data.get("rank"), int)
        assert isinstance(ev.data.get("reasoning"), str)


@pytest.mark.asyncio
async def test_no_clarify_event_on_full_profile(
    chat_client: httpx.AsyncClient,
) -> None:
    status, events, _ = await consume_sse(
        chat_client,
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Smoky leather for winter evenings, masc, intensity strong, budget high"
                    ),
                }
            ]
        },
    )
    assert status == 200
    assert not [e for e in events if e.event == "clarify"], (
        "full profile should not trigger clarify"
    )
