"""Clarify node — emits one targeted question, terminates the turn.

Per agent spec "Clarify Node": gpt-4o-mini, asks ONE question. Tagged via
`additional_kwargs={"chat_event": "clarify"}` so the SSE adapter detects the
turn-terminator and emits `done(clarify)`.

On OpenAI failure, falls through to a static generic clarify question so the
turn still terminates cleanly — api-app spec "Chat Degraded-Mode Fallback".
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from openai import APIConnectionError, APIError, APITimeoutError

from ..constants import MAX_TOKENS_CLARIFY, MODEL_FAST, REQUIRED_PROFILE_FIELDS
from ..prompts.clarify import CLARIFY_SYSTEM_PROMPT
from ..state import State

GENERIC_CLARIFY = "I can help recommend fragrances. What kind are you looking for?"


async def clarify_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    prefs = state.get("preferences") or {}
    missing = [f for f in REQUIRED_PROFILE_FIELDS if not prefs.get(f)]
    client = (config.get("configurable") or {})["openai_client"]
    payload = json.dumps({"missing_fields": missing, "have": prefs})
    degraded = bool(state.get("degraded", False))
    error = state.get("error")
    try:
        completion = await client.chat.completions.create(
            model=MODEL_FAST,
            max_tokens=MAX_TOKENS_CLARIFY,
            temperature=0.2,
            messages=[
                {"role": "system", "content": CLARIFY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"<<<USER_DATA>>>{payload}<<<END>>>",
                },
            ],
        )
        question = (completion.choices[0].message.content or "").strip() or GENERIC_CLARIFY
    except (APIError, APITimeoutError, APIConnectionError):
        question = GENERIC_CLARIFY
        degraded = True
        if not error:
            error = "openai_clarify_failed"
    extra: dict[str, Any] = {"chat_event": "clarify"}
    if error:
        extra["error"] = error
    update: dict[str, Any] = {
        "messages": [AIMessage(content=question, additional_kwargs=extra)],
    }
    if degraded:
        update["degraded"] = True
    if error:
        update["error"] = error
    return update
