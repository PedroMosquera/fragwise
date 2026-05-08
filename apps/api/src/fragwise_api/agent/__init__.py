"""LangGraph 1.x recommendation agent package.

Re-exports the canonical surface used by the chat router and integration
tests. The compiled `StateGraph` is constructed at first import of `.graph`.
"""

from __future__ import annotations

from .state import FragranceCandidate, Pick, State

__all__ = [
    "FragranceCandidate",
    "Pick",
    "State",
    "compiled",
]


def __getattr__(name: str) -> object:
    """Lazy-load `compiled` so importing the package does not transitively
    import every node module (and thus `langchain_core` / `openai`) before
    the caller actually needs the graph. Keeps `import fragwise_api.agent`
    cheap for sites that only need the dataclasses or `State`."""

    if name == "compiled":
        from .graph import compiled

        return compiled
    raise AttributeError(f"module 'fragwise_api.agent' has no attribute {name!r}")
