"""Overflow paths: empty messages, last not user, char cap, count cap, token
cap (api-app spec: Chat Conversation Length Cap + Chat Message Token Cap)."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_empty_messages_returns_422(chat_client: httpx.AsyncClient) -> None:
    r = await chat_client.post("/api/v1/chat", json={"messages": []})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "invalid_params"


@pytest.mark.asyncio
async def test_last_message_must_be_user(chat_client: httpx.AsyncClient) -> None:
    r = await chat_client.post(
        "/api/v1/chat",
        json={
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "invalid_params"


@pytest.mark.asyncio
async def test_too_many_messages_returns_422(chat_client: httpx.AsyncClient) -> None:
    msgs = [{"role": "user", "content": "x"} for _ in range(21)]
    r = await chat_client.post("/api/v1/chat", json={"messages": msgs})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "invalid_params"


@pytest.mark.asyncio
async def test_message_token_cap_returns_422(chat_client: httpx.AsyncClient) -> None:
    """>1000-token message via tiktoken -> 422 message_too_long.

    `gpt-4o-mini` uses `o200k_base`. `"! "` encodes to two distinct tokens
    in that vocabulary, so repeating it 1001x gives ~1002 tokens at only
    ~2002 chars — well under the 4000-char pre-check, so the tokenizer
    branch is exercised."""
    content = "! " * 1001  # ~1002 tokens, ~2002 chars
    r = await chat_client.post(
        "/api/v1/chat", json={"messages": [{"role": "user", "content": content}]}
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "message_too_long"
    assert body["error"]["detail"]["max_tokens"] == 1000


@pytest.mark.asyncio
async def test_message_char_cap_returns_422(chat_client: httpx.AsyncClient) -> None:
    """4001-character message hits the cheap pre-check before tokenizing."""
    content = "x" * 4001
    r = await chat_client.post(
        "/api/v1/chat", json={"messages": [{"role": "user", "content": content}]}
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "invalid_params"
