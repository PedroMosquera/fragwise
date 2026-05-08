"""Grounding invariant: SSE adapter drops picks whose slug is not in the
explain node's `candidate_slugs` allow-list (agent spec: Grounding
Invariant; ADR-0035).

Covers BOTH agent-spec scenarios:
  (a) "Hallucinated pick is dropped" — 1 of N picks is unknown -> N-1
      `recommendation` events + `done(complete)`.
  (b) "All-hallucinated output degrades" — every pick is unknown -> 0
      recommendations, `degraded(no_grounded_picks)` + `done(degraded)`.
"""

from __future__ import annotations

import httpx
import pytest

from .conftest import StubScript, consume_sse

pytestmark = pytest.mark.integration


@pytest.fixture()
def stub_openai_script_partial() -> StubScript:
    """3 grounded slugs + 1 hallucinated slug. Intake omits both gender
    and families so retrieve does not exclude any seeded fragrance via the
    ontology filter; rank keeps all three above the 0.3 threshold."""
    return StubScript(
        intake_prefs={
            "occasion": "evening",
            "season": "winter",
            "intensity": "strong",
            # No `families` -> no accord filter -> all seeded rows in candidates.
            "budget": "high",
        },
        explain_picks=[
            {"slug": "aventus", "rank": 1, "reasoning": "Smoky leather signature."},
            {"slug": "sauvage", "rank": 2, "reasoning": "Smoky alternative."},
            {"slug": "miss-dior", "rank": 3, "reasoning": "Lighter feminine pick."},
            {
                "slug": "phantom-fragrance",
                "rank": 4,
                "reasoning": "This slug was never in the candidate list.",
            },
        ],
    )


@pytest.fixture()
def stub_openai_script_all_hallucinated() -> StubScript:
    return StubScript(
        explain_picks=[
            {"slug": "phantom-1", "rank": 1, "reasoning": "Unknown 1."},
            {"slug": "phantom-2", "rank": 2, "reasoning": "Unknown 2."},
            {"slug": "phantom-3", "rank": 3, "reasoning": "Unknown 3."},
        ]
    )


@pytest.mark.asyncio
async def test_partial_hallucination_drops_unknown_pick(
    chat_engine,  # type: ignore[no-untyped-def]
    chat_seeded,  # type: ignore[no-untyped-def]
    fake_redis,  # type: ignore[no-untyped-def]
    stub_openai_script_partial: StubScript,
) -> None:
    """Spec scenario (a): 4 picks, 1 hallucinated -> 3 recommendation events."""
    from .conftest import StubAsyncOpenAI, _make_chat_app

    stub = StubAsyncOpenAI(stub_openai_script_partial)
    app = _make_chat_app(chat_engine, fake_redis, stub)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        status, events, err = await consume_sse(
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
    assert status == 200, err
    rec_events = [e for e in events if e.event == "recommendation"]
    # F-equivalent assertion per orchestrator brief: hallucinated pick MUST
    # be dropped at the SSE adapter; grounded picks survive.
    assert len(rec_events) == 3, (
        f"expected exactly 3 grounded recommendations after dropping the "
        f"hallucinated slug; got {len(rec_events)}"
    )
    slugs = {e.data["fragrance"]["slug"] for e in rec_events}
    assert "phantom-fragrance" not in slugs
    assert events[-1].event == "done"
    assert events[-1].data["finish_reason"] == "complete"


@pytest.mark.asyncio
async def test_all_hallucinated_degrades(
    chat_engine,  # type: ignore[no-untyped-def]
    chat_seeded,  # type: ignore[no-untyped-def]
    fake_redis,  # type: ignore[no-untyped-def]
    stub_openai_script_all_hallucinated: StubScript,
) -> None:
    """Spec scenario (b): every pick is unknown -> degraded + done(degraded)."""
    from .conftest import StubAsyncOpenAI, _make_chat_app

    stub = StubAsyncOpenAI(stub_openai_script_all_hallucinated)
    app = _make_chat_app(chat_engine, fake_redis, stub)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        status, events, err = await consume_sse(
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
    assert status == 200, err
    rec_events = [e for e in events if e.event == "recommendation"]
    assert rec_events == [], "no grounded picks expected"
    degraded_events = [e for e in events if e.event == "degraded"]
    assert any(d.data.get("reason") == "no_grounded_picks" for d in degraded_events)
    assert events[-1].event == "done"
    assert events[-1].data["finish_reason"] == "degraded"
