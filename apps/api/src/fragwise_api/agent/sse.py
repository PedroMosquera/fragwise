"""SSE adapter: LangGraph events -> SSE wire events.

Encodes the canonical agent-spec event schema (`event: <type>\\n` +
`data: <json>\\n\\n`). The grounding validator drops any `recommendation`
whose pick slug is absent from the explain node's `candidate_slugs`
allow-list (ADR-0035; defense-in-depth alongside the prompt). Cancellation
safety per ADR-0036: re-raise `asyncio.CancelledError` after best-effort
cleanup so OpenAI streams cancel cleanly.

Per api-app spec "Chat Degraded-Mode Fallback":
  - intake failure -> `degraded(openai_intake_failed)` then a fall-through
    generic `clarify` then `done(degraded)`.
  - retrieve embedding failure -> `degraded(openai_embedding_failed)` then
    pipeline continues, `done(complete)`.
  - rank failure -> `degraded(openai_rank_failed)`, pipeline continues using
    retrieval order, `done(degraded)`.
  - explain failure -> `degraded(openai_explain_failed)`, no recommendations,
    `done(degraded)`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage

from .state import FragranceCandidate

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict[str, Any]) -> bytes:
    """Encode one SSE event per the agent spec wire format."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def _validate_pick(line: str, allowed: set[str]) -> dict[str, Any] | None:
    """Parse one NDJSON pick line; drop if `slug` is absent from `allowed`."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    slug = obj.get("slug")
    if not isinstance(slug, str) or slug not in allowed:
        logger.warning("grounding_dropped slug=%s", slug)
        return None
    return obj


_ERROR_TO_DEGRADED: dict[str, str] = {
    "openai_intake_failed": "openai_intake_failed",
    "openai_clarify_failed": "openai_clarify_failed",
    "openai_rank_failed": "openai_rank_failed",
    "openai_embedding_failed": "openai_embedding_failed",
    "openai_explain_failed": "openai_explain_failed",
}


async def stream_chat_response(
    graph: Any,
    inputs: dict[str, Any],
    config: dict[str, Any],
    candidate_lookup: dict[str, FragranceCandidate],
) -> AsyncIterator[bytes]:
    """Translate `graph.astream(stream_mode="messages")` into SSE bytes.

    `candidate_lookup` is mutated in-place by the caller as state snapshots
    arrive (the router wraps `astream` and forwards updates here). For the
    pure-message stream we rely on the explain node's `candidate_slugs`
    allow-list for grounding; the lookup is consulted to enrich the emitted
    `recommendation` payload with display fields.
    """
    finish_reason = "complete"
    grounded_count = 0
    explain_seen = False
    emitted_degraded_codes: set[str] = set()

    def _emit_degraded(code: str, fallback: str) -> bytes | None:
        if code in emitted_degraded_codes:
            return None
        emitted_degraded_codes.add(code)
        return _sse("degraded", {"reason": code, "fallback": fallback})

    try:
        async for chunk, _meta in graph.astream(inputs, config=config, stream_mode="messages"):
            if isinstance(chunk, AIMessage):
                kwargs = chunk.additional_kwargs or {}
                kind = kwargs.get("chat_event")
                err = kwargs.get("error")
                # Per-node degraded signalling: emit BEFORE the node's
                # primary event so clients can render the warning inline.
                if isinstance(err, str) and err in _ERROR_TO_DEGRADED:
                    fallback = (
                        "generic_clarify"
                        if err == "openai_intake_failed"
                        else (
                            "fts"
                            if err == "openai_embedding_failed"
                            else ("retrieval_order" if err == "openai_rank_failed" else "top1")
                        )
                    )
                    payload = _emit_degraded(_ERROR_TO_DEGRADED[err], fallback)
                    if payload is not None:
                        yield payload

                content = chunk.content if isinstance(chunk.content, str) else ""
                if kind == "clarify":
                    yield _sse("clarify", {"question": content})
                    finish_reason = "clarify" if not err else "degraded"
                elif kind == "explain":
                    explain_seen = True
                    allowed = set(kwargs.get("candidate_slugs") or [])
                    # `candidate_lookup` from explain's additional_kwargs is
                    # the authoritative display-field source (pre-resolved
                    # by the retrieve node). The router-supplied lookup is a
                    # fallback in case explain output omits the dict.
                    inline_lookup_raw = kwargs.get("candidate_lookup") or {}
                    inline_lookup: dict[str, dict[str, Any]] = (
                        inline_lookup_raw if isinstance(inline_lookup_raw, dict) else {}
                    )
                    for line in content.splitlines():
                        pick = _validate_pick(line, allowed)
                        if pick is None:
                            continue
                        slug = pick["slug"]
                        inline = inline_lookup.get(slug)
                        if isinstance(inline, dict):
                            display = {
                                "slug": str(inline.get("slug", slug)),
                                "name": str(inline.get("name", "")),
                                "brand_slug": str(inline.get("brand_slug", "")),
                            }
                            match_reason = list(inline.get("match_reason") or [])
                        else:
                            cand = candidate_lookup.get(slug)
                            if cand is None:
                                logger.warning("grounding_lookup_miss slug=%s", slug)
                                continue
                            display = {
                                "slug": cand.slug,
                                "name": cand.name,
                                "brand_slug": cand.brand_slug,
                            }
                            match_reason = list(cand.match_reason)
                        rank = pick.get("rank", grounded_count + 1)
                        try:
                            rank = int(rank)
                        except (TypeError, ValueError):
                            rank = grounded_count + 1
                        reasoning = pick.get("reasoning", "")
                        yield _sse(
                            "recommendation",
                            {
                                "fragrance": display,
                                "reasoning": reasoning,
                                "rank": rank,
                                "match_reason": match_reason,
                            },
                        )
                        grounded_count += 1
                        yield _sse("token", {"text": reasoning})
                elif kind == "explain_failed":
                    payload = _emit_degraded("openai_explain_failed", "top1")
                    if payload is not None:
                        yield payload
                    finish_reason = "degraded"
                elif kind == "no_candidates":
                    # Retrieve returned zero rows. Nothing to recommend; mark
                    # as degraded so clients render an empty-state.
                    payload = _emit_degraded("no_grounded_picks", "none")
                    if payload is not None:
                        yield payload
                    finish_reason = "degraded"
        # End-of-stream grounding check: explain ran but every pick was
        # dropped -> degraded(no_grounded_picks) per agent spec.
        if (
            explain_seen
            and grounded_count == 0
            and "openai_explain_failed" not in emitted_degraded_codes
        ):
            payload = _emit_degraded("no_grounded_picks", "none")
            if payload is not None:
                yield payload
            finish_reason = "degraded"
    except asyncio.CancelledError:
        # ADR-0036: re-raise after best-effort cleanup. Closing the astream
        # generator cancels the underlying OpenAI calls.
        logger.info("chat_stream_cancelled")
        raise
    except Exception as exc:
        logger.exception("chat_stream_error")
        yield _sse("error", {"code": "internal", "message": str(exc)[:200]})
        finish_reason = "error"
    finally:
        # Always emit `done` last (agent spec: SSE Event Schema).
        yield _sse("done", {"finish_reason": finish_reason})
