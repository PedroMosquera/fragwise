"""Clarify path: sparse preferences -> exactly one `clarify` event then
`done(clarify)` (agent spec scenario "Clarify-path terminates with
done(clarify)")."""

from __future__ import annotations

import httpx
import pytest

from .conftest import StubScript, consume_sse

pytestmark = pytest.mark.integration


@pytest.fixture()
def stub_openai_script() -> StubScript:
    """Force intake to return a sparse profile (only `families`) so the
    `_needs_clarification` predicate trips the clarify branch."""
    return StubScript(intake_prefs={"families": ["leather"]})


@pytest.mark.asyncio
async def test_sparse_profile_triggers_one_clarify(
    chat_client: httpx.AsyncClient,
) -> None:
    status, events, err = await consume_sse(
        chat_client,
        {"messages": [{"role": "user", "content": "Hi I'd like something nice"}]},
    )
    assert status == 200, err
    clarify_events = [e for e in events if e.event == "clarify"]
    assert len(clarify_events) == 1, f"expected exactly 1 clarify; got {len(clarify_events)}"
    assert isinstance(clarify_events[0].data.get("question"), str)
    assert events[-1].event == "done"
    assert events[-1].data["finish_reason"] == "clarify"
    # Retrieve / rank / explain must NOT have run; no `recommendation` events.
    assert not [e for e in events if e.event == "recommendation"]
