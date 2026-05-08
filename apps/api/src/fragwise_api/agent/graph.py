"""StateGraph composition. Compiled once at import time — NO checkpointer.

Per agent spec "No Checkpointer In V1" + ADR-0039: conditional clarify edge
from `intake` (not a separate routing node). State is round-tripped via the
request body's `messages[]` array; `session_id` is opaque telemetry only.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .constants import CLARIFY_MISSING_THRESHOLD, REQUIRED_PROFILE_FIELDS
from .nodes.clarify import clarify_node
from .nodes.explain import explain_node
from .nodes.intake import intake_node
from .nodes.rank import rank_node
from .nodes.retrieve import retrieve_node
from .state import State


def _needs_clarification(state: State) -> str:
    """Conditional-edge predicate: returns 'clarify' or 'retrieve'."""
    prefs = state.get("preferences") or {}
    missing = sum(1 for f in REQUIRED_PROFILE_FIELDS if not prefs.get(f))
    return "clarify" if missing >= CLARIFY_MISSING_THRESHOLD else "retrieve"


def _build() -> Any:
    g: Any = StateGraph(State)
    g.add_node("intake", intake_node)
    g.add_node("clarify", clarify_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("rank", rank_node)
    g.add_node("explain", explain_node)

    g.add_edge(START, "intake")
    g.add_conditional_edges(
        "intake",
        _needs_clarification,
        {"clarify": "clarify", "retrieve": "retrieve"},
    )
    g.add_edge("clarify", END)
    g.add_edge("retrieve", "rank")
    g.add_edge("rank", "explain")
    g.add_edge("explain", END)
    return g


# Public surface: compiled module-level singleton. Per ADR (no checkpointer).
compiled: Any = _build().compile()
