"""POST /api/v1/chat — SSE chat endpoint.

Validates body (length + role + token cap), increments the chat daily
counter (raises 503 over-cap), then opens a `text/event-stream` response.
Per-IP rate limits are layered via stacked `@chat_limiter.limit()`
decorators (path "a" from design note; verified via Context7) — each
window is enforced independently.

Per ADR-0033 + agent spec "Retrieve Node": graph runs in-process; no HTTP
loopback. The stream is `app.astream(stream_mode="messages")` translated
into SSE bytes by `agent.sse.stream_chat_response`. Cancellation safety is
inherited from the SSE adapter (ADR-0036).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from openai import AsyncOpenAI
from redis.asyncio import Redis

from fragwise_api.api.v1.errors import ApiError

from .constants import MAX_TOKENS_PER_MESSAGE
from .daily_limit import (
    ChatDailyLimitReached,
    chat_daily_limit_value,
    chat_increment_and_check,
)
from .rate_limit import chat_limiter, per_ip_day, per_ip_hour
from .schemas import ChatRequest
from .sse import stream_chat_response
from .state import FragranceCandidate

router = APIRouter(prefix="/api/v1", tags=["Chat"])


# Dependency factories — mirror search/router.py.


def get_redis_dep(request: Request) -> Redis:
    return request.app.state.redis  # type: ignore[no-any-return]


def get_openai_dep(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client  # type: ignore[no-any-return]


RedisDep = Annotated[Redis, Depends(get_redis_dep)]
OpenAIDep = Annotated[AsyncOpenAI, Depends(get_openai_dep)]


def _kill_switch_error() -> ApiError:
    return ApiError(
        status_code=503,
        code="daily_limit_reached",
        message="daily chat budget exhausted",
        detail=None,
    )


def _too_long_error(idx: int, max_tokens: int) -> ApiError:
    return ApiError(
        status_code=422,
        code="message_too_long",
        message="one or more messages exceed the per-message token cap",
        detail={"index": idx, "max_tokens": max_tokens},
    )


def _to_lc_messages(req: ChatRequest) -> list[Any]:
    """Map the API ChatMessage envelope to LangChain message types."""
    out: list[Any] = []
    for m in req.messages:
        if m.role == "user":
            out.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            out.append(AIMessage(content=m.content))
        else:
            out.append(SystemMessage(content=m.content))
    return out


@router.post("/chat")
@chat_limiter.limit(per_ip_hour)
@chat_limiter.limit(per_ip_day)
async def chat(
    request: Request,
    body: ChatRequest,
    redis: RedisDep,
    openai_client: OpenAIDep,
) -> StreamingResponse:
    """Stream a fragrance recommendation turn as SSE events.

    Pre-stream gates run in this order (all errors return JSON envelopes
    BEFORE the stream opens):

      1. Pydantic body validation (last-must-be-user, char + count caps).
      2. tiktoken per-message token count vs `MAX_TOKENS_PER_MESSAGE`.
      3. Redis daily kill-switch INCR + cap.
      4. slowapi per-IP h + d windows (decorators above).
    """
    encoder = request.app.state.tiktoken_encoder
    for i, m in enumerate(body.messages):
        if len(encoder.encode(m.content)) > MAX_TOKENS_PER_MESSAGE:
            raise _too_long_error(i, MAX_TOKENS_PER_MESSAGE)

    now = datetime.now(UTC)
    try:
        await chat_increment_and_check(redis, chat_daily_limit_value(), now)
    except ChatDailyLimitReached as err:
        raise _kill_switch_error() from err

    # Lazy-import the compiled graph so OpenAPI generation does not pay the
    # node import cost when the chat endpoint is unused.
    from .graph import compiled

    sm = request.app.state.db_sessionmaker
    config = {
        "configurable": {
            "openai_client": openai_client,
            "db_sessionmaker": sm,
            "redis": redis,
        }
    }
    inputs = {"messages": _to_lc_messages(body)}

    cand_lookup: dict[str, FragranceCandidate] = {}

    async def gen() -> AsyncIterator[bytes]:
        # Tap state snapshots from a parallel `astream(stream_mode="updates")`
        # so the SSE adapter has the candidate lookup available at explain
        # time. Single-shot pre-walk: run the graph once, collect candidates
        # from the retrieve node, then run again for SSE — wasteful. Cheaper
        # path: feed updates into the lookup as they fly past the SSE adapter.
        async for ev in stream_chat_response(compiled, inputs, config, cand_lookup):
            yield ev

    headers = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers=headers,
    )
