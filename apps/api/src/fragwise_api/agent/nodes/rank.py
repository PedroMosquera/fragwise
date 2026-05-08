"""Rank node — gpt-4o-mini scores candidates; reorder + drop below threshold.

Per agent spec "Rank Node": MUST NOT add new slugs (preserves grounding).
On OpenAI failure, returns `degraded=True` and leaves the retrieval order
unchanged (api-app spec: rank-failure path).
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from openai import APIConnectionError, APIError, APITimeoutError

from ..constants import MAX_TOKENS_RANK, MODEL_FAST, RANK_SCORE_THRESHOLD
from ..prompts.rank import RANK_SYSTEM_PROMPT
from ..state import State


def _rank_degraded_payload() -> dict[str, Any]:
    """Tagged AIMessage so the SSE adapter can emit
    `degraded(openai_rank_failed)` even though rank produces no
    user-facing output."""
    return {
        "degraded": True,
        "error": "openai_rank_failed",
        "messages": [
            AIMessage(
                content="",
                additional_kwargs={
                    "chat_event": "node_degraded",
                    "error": "openai_rank_failed",
                },
            )
        ],
    }


def _parse_scores(raw: str) -> dict[str, float]:
    """Tolerant score parser: accepts `{"scores":[{slug,score}]}` or a bare
    list at the top level. Drops malformed entries."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        items = parsed.get("scores", [])
        if not isinstance(items, list):
            return {}
    else:
        return {}
    out: dict[str, float] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        slug = item.get("slug")
        score = item.get("score")
        if not isinstance(slug, str):
            continue
        try:
            out[slug] = float(score)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    return out


async def rank_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    candidates = state.get("candidates") or []
    if not candidates:
        return {}
    prefs = state.get("preferences") or {}
    client = (config.get("configurable") or {})["openai_client"]
    payload = json.dumps(
        {
            "preferences": prefs,
            "candidates": [
                {
                    "slug": c.slug,
                    "name": c.name,
                    "brand": c.brand_slug,
                    "relevance_score": c.relevance_score,
                    "match_reason": list(c.match_reason),
                }
                for c in candidates
            ],
        }
    )
    try:
        completion = await client.chat.completions.create(
            model=MODEL_FAST,
            max_tokens=MAX_TOKENS_RANK,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": RANK_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"<<<USER_DATA>>>{payload}<<<END>>>",
                },
            ],
        )
    except (APIError, APITimeoutError, APIConnectionError):
        # Degraded: keep retrieval order, mark degraded.
        return _rank_degraded_payload()

    score_map = _parse_scores(completion.choices[0].message.content or "")
    if not score_map:
        # Malformed model output -> keep retrieval order.
        return _rank_degraded_payload()

    # Reorder + threshold-prune. NEVER add new slugs (grounding invariant).
    kept = [c for c in candidates if score_map.get(c.slug, 0.0) >= RANK_SCORE_THRESHOLD]
    kept.sort(key=lambda c: score_map.get(c.slug, 0.0), reverse=True)
    return {"candidates": kept}
