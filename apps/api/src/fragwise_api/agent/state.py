"""TypedDict State + dataclasses for retrieved/ranked candidates.

Per agent spec "State Shape": `messages` is annotated with the
`langgraph.graph.message.add_messages` reducer so node returns accumulate
rather than overwrite. `total=False` lets early nodes write subsets without
satisfying every key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, TypedDict
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


@dataclass(frozen=True)
class FragranceCandidate:
    """One retrieved fragrance row, ready for ranking and grounding checks.

    Mirrors `search.retrieval.RetrievalRow` but carries the slug + display
    name pre-resolved so explain/rank prompts can reference them without
    re-querying the DB. The `slug` field is the grounding key.
    """

    fragrance_id: UUID
    slug: str
    name: str
    brand_slug: str
    relevance_score: float
    match_reason: list[str]


@dataclass(frozen=True)
class Pick:
    """One finalized recommendation produced by the explain node.

    `candidate.slug` MUST appear in `state.candidates` — enforced by the SSE
    grounding validator. `reasoning` is the user-facing rationale paragraph.
    """

    candidate: FragranceCandidate
    reasoning: str
    rank: int


class State(TypedDict, total=False):
    """LangGraph state. `total=False` lets early nodes write subsets."""

    messages: Annotated[list[BaseMessage], add_messages]
    preferences: dict[str, Any] | None
    candidates: list[FragranceCandidate]
    picks: list[Pick]
    degraded: bool
    error: str | None
