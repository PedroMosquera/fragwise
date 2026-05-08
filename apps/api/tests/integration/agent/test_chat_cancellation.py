"""Cancellation safety: client closes mid-stream -> CancelledError propagates
+ stub OpenAI stream's `aclose` was called (agent spec: Cancellation Safety;
ADR-0036)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from .conftest import StubAsyncOpenAI, StubScript, _make_chat_app

pytestmark = pytest.mark.integration


class _SlowStreamIterator:
    """Async iterator that pauses between chunks long enough for a client
    cancellation to land mid-stream."""

    def __init__(self, lines: list[str], delay: float = 0.5) -> None:
        self._lines = lines
        self._i = 0
        self._delay = delay
        self.aclose_called = False

    def __aiter__(self) -> _SlowStreamIterator:
        return self

    async def __anext__(self):
        if self._i >= len(self._lines):
            raise StopAsyncIteration
        await asyncio.sleep(self._delay)
        line = self._lines[self._i]
        self._i += 1
        from .conftest import _StreamEvent

        return _StreamEvent(line)

    async def aclose(self) -> None:
        self.aclose_called = True


@pytest.mark.asyncio
async def test_client_disconnect_cancels_openai_stream(
    chat_engine,  # type: ignore[no-untyped-def]
    chat_seeded,  # type: ignore[no-untyped-def]
    fake_redis,  # type: ignore[no-untyped-def]
) -> None:
    import json as _json

    slow_stream = _SlowStreamIterator(
        [
            _json.dumps({"slug": "aventus", "rank": 1, "reasoning": "Smoky leather signature."})
            + "\n",
            _json.dumps({"slug": "sauvage", "rank": 2, "reasoning": "Fresher smoky alternative."})
            + "\n",
        ],
        delay=0.5,
    )
    stub = StubAsyncOpenAI(StubScript())
    # Patch the stub's chat.completions.create to return the slow stream
    # whenever the explain phase fires.
    original_create = stub.chat.completions.create

    async def patched_create(**kwargs):  # type: ignore[no-untyped-def]
        for m in kwargs.get("messages", []):
            if isinstance(m, dict) and "explain stage" in (m.get("content") or ""):
                return slow_stream
        return await original_create(**kwargs)

    stub.chat.completions.create = patched_create  # type: ignore[method-assign]

    app = _make_chat_app(chat_engine, fake_redis, stub)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", timeout=2.0
    ) as client:
        # Open the stream then cancel mid-way by exiting the context manager
        # before fully draining.
        try:
            async with client.stream(
                "POST",
                "/api/v1/chat",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Smoky leather masc winter evening, intensity strong, budget high"
                            ),
                        }
                    ]
                },
            ) as resp:
                assert resp.status_code == 200
                # Read a few bytes then break out.
                async for _chunk in resp.aiter_text():
                    break  # client disconnect
        except (httpx.ReadError, httpx.RemoteProtocolError):
            # Client-side aborts surface as transport errors.
            pass

    # Allow the server to observe the disconnect and run cleanup.
    await asyncio.sleep(0.1)
    assert slow_stream.aclose_called, (
        "explain stream's aclose() must be called on client disconnect"
    )
