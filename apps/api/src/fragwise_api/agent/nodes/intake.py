"""Intake node — extracts structured preferences from latest user message.

Uses `gpt-4o-mini` in JSON mode. Skips OpenAI for trivially-short messages
(below `INTAKE_MIN_CHARS`) so clarify takes over. On `APIError`, returns a
degraded signal that the SSE adapter renders as a `degraded` event then a
generic clarify (api-app spec: Chat Degraded-Mode Fallback).
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from openai import APIConnectionError, APIError, APITimeoutError

from ..constants import INTAKE_MIN_CHARS, MAX_TOKENS_INTAKE, MODEL_FAST
from ..prompts.intake import INTAKE_SYSTEM_PROMPT
from ..state import State


def _last_user_text(state: State) -> str:
    """Return the latest `HumanMessage.content` or `""`."""
    msgs = state.get("messages") or []
    for m in reversed(msgs):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


async def intake_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    """Extract preferences. Skips OpenAI for trivially-short messages."""
    text = _last_user_text(state).strip()
    if len(text) < INTAKE_MIN_CHARS:
        return {"preferences": {}}  # missing-field signal -> clarify

    client = (config.get("configurable") or {})["openai_client"]
    user_payload = json.dumps({"message": text})
    try:
        completion = await client.chat.completions.create(
            model=MODEL_FAST,
            max_tokens=MAX_TOKENS_INTAKE,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"<<<USER_DATA>>>{user_payload}<<<END>>>",
                },
            ],
        )
    except (APIError, APITimeoutError, APIConnectionError):
        # Degraded: signal via a tagged AIMessage so the SSE adapter emits
        # `degraded(openai_intake_failed)`. Empty preferences ensure the
        # clarify branch fires for the generic-clarify fall-through.
        return {
            "preferences": {},
            "degraded": True,
            "error": "openai_intake_failed",
            "messages": [
                AIMessage(
                    content="",
                    additional_kwargs={
                        "chat_event": "node_degraded",
                        "error": "openai_intake_failed",
                    },
                )
            ],
        }
    raw = completion.choices[0].message.content or "{}"
    try:
        prefs = json.loads(raw)
    except json.JSONDecodeError:
        prefs = {}
    if isinstance(prefs, dict) and prefs.get("refused"):
        return {"preferences": {}, "error": "off_topic"}
    if not isinstance(prefs, dict):
        prefs = {}
    return {"preferences": prefs}
