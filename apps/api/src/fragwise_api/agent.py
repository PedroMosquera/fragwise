"""LangGraph 1.x stub. Proves install + import shape; no LangChain."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import START, StateGraph


class AgentState(TypedDict):
    text: str


def echo(state: AgentState) -> AgentState:
    """Identity node — replaced in later phases by real chat orchestration."""
    return {"text": state["text"]}


def build_graph() -> StateGraph:  # type: ignore[type-arg]
    graph: StateGraph = StateGraph(AgentState)  # type: ignore[type-arg]
    graph.add_node("echo", echo)
    graph.add_edge(START, "echo")
    return graph


compiled = build_graph().compile()
