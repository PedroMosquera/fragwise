"""Explain node — gpt-4o `stream=True`; emits a single AIMessage carrying
the accumulated NDJSON pick stream + a `candidate_slugs` allow-list.

LangGraph passes streaming events through `astream(stream_mode="messages")`
when the node uses an LLM with `stream=True`; the SSE adapter parses the
final AIMessage's NDJSON content and validates each pick's slug against the
allow-list (defense-in-depth grounding — ADR-0035).

On OpenAI failure (api-app spec: explain-failure path), returns a tagged
`AIMessage(chat_event="explain_failed")` plus `degraded=True` so the SSE
adapter emits `degraded(openai_explain_failed)` + `done(degraded)`.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from openai import APIConnectionError, APIError, APITimeoutError

from ..constants import MAX_TOKENS_EXPLAIN, MODEL_SMART, PICK_COUNT_MAX
from ..prompts.explain import EXPLAIN_SYSTEM_PROMPT
from ..state import State


async def explain_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    candidates = state.get("candidates") or []
    if not candidates:
        return {
            "messages": [
                AIMessage(
                    content="",
                    additional_kwargs={"chat_event": "no_candidates"},
                )
            ]
        }

    prefs = state.get("preferences") or {}
    client = (config.get("configurable") or {})["openai_client"]
    top = candidates[:PICK_COUNT_MAX]
    payload = json.dumps(
        {
            "preferences": prefs,
            "candidates": [
                {
                    "slug": c.slug,
                    "name": c.name,
                    "brand": c.brand_slug,
                    "score": c.relevance_score,
                    "match_reason": list(c.match_reason),
                }
                for c in top
            ],
        }
    )

    try:
        stream = await client.chat.completions.create(
            model=MODEL_SMART,
            max_tokens=MAX_TOKENS_EXPLAIN,
            temperature=0.4,
            stream=True,
            messages=[
                {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"<<<USER_DATA>>>{payload}<<<END>>>",
                },
            ],
        )
    except (APIError, APITimeoutError, APIConnectionError):
        return {
            "messages": [
                AIMessage(
                    content="",
                    additional_kwargs={
                        "chat_event": "explain_failed",
                        "candidate_slugs": [c.slug for c in candidates],
                    },
                )
            ],
            "degraded": True,
            "error": "openai_explain_failed",
        }

    chunks: list[str] = []
    try:
        async for ev in stream:
            choices = getattr(ev, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None) if delta is not None else None
            if content:
                chunks.append(str(content))
    except (APIError, APITimeoutError, APIConnectionError):
        # Mid-stream failure: render what we got, mark degraded.
        return {
            "messages": [
                AIMessage(
                    content="".join(chunks),
                    additional_kwargs={
                        "chat_event": "explain_failed",
                        "candidate_slugs": [c.slug for c in candidates],
                    },
                )
            ],
            "degraded": True,
            "error": "openai_explain_failed",
        }
    finally:
        # Best-effort cleanup; if the OpenAI client supports `aclose`, run it
        # so token billing stops on cancellation paths.
        aclose = getattr(stream, "aclose", None)
        if callable(aclose):
            import contextlib

            with contextlib.suppress(Exception):
                await aclose()

    return {
        "messages": [
            AIMessage(
                content="".join(chunks),
                additional_kwargs={
                    "chat_event": "explain",
                    "candidate_slugs": [c.slug for c in candidates],
                    # Pre-resolved display fields so the SSE adapter does not
                    # need to round-trip state snapshots for grounding.
                    "candidate_lookup": {
                        c.slug: {
                            "slug": c.slug,
                            "name": c.name,
                            "brand_slug": c.brand_slug,
                            "match_reason": list(c.match_reason),
                        }
                        for c in candidates
                    },
                },
            )
        ],
    }
