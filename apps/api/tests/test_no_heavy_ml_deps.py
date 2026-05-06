"""Regression test: LangGraph install MUST NOT pull torch/transformers."""

from __future__ import annotations

import importlib.util


def test_torch_not_installed() -> None:
    assert importlib.util.find_spec("torch") is None, (
        "torch leaked into the dependency closure — check `uv tree` and prune."
    )


def test_transformers_not_installed() -> None:
    assert importlib.util.find_spec("transformers") is None, (
        "transformers leaked into the dependency closure — check `uv tree` and prune."
    )


def test_sentence_transformers_not_installed() -> None:
    assert importlib.util.find_spec("sentence_transformers") is None, (
        "sentence-transformers leaked in — not allowed in 0b."
    )


def test_langchain_not_installed() -> None:
    assert importlib.util.find_spec("langchain") is None, (
        "langchain leaked in — 0b is langgraph-only."
    )
