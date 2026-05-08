"""LangGraph node modules for the chat agent.

Each node module exposes a single async function `<name>_node(state, config)`
returning a partial-`State` dict. Nodes are wired together by `agent/graph.py`.
"""

from __future__ import annotations
