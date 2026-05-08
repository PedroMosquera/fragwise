"""Pydantic v2 request schemas for the chat endpoint.

Response is SSE — no Pydantic response model. Each SSE event payload is
documented in the agent spec and mirrored in `sse.py`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import MAX_CHARS_PER_MESSAGE, MAX_MESSAGES


class ChatMessage(BaseModel):
    """One conversation message. `role=user|assistant|system` per the
    api-app spec request body. `content` is char-capped here as a cheap
    pre-check before tokenization (see `MAX_TOKENS_PER_MESSAGE`)."""

    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=MAX_CHARS_PER_MESSAGE)


class ChatRequest(BaseModel):
    """`POST /api/v1/chat` body.

    `session_id` is opaque telemetry per agent spec "No Checkpointer In V1"
    — never used to drive any state-store read or write.
    """

    model_config = ConfigDict(extra="forbid")
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)
    session_id: str | None = Field(default=None, max_length=128)

    @field_validator("messages")
    @classmethod
    def _last_must_be_user(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if not v or v[-1].role != "user":
            raise ValueError("last message must have role='user'")
        return v
