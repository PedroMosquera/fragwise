"""Immutable system prompts for the LangGraph chat agent.

Per agent spec "Prompt-Injection Hardening": each prompt is a module-level
constant. Nodes MUST import them; they MUST NOT be string-interpolated with
user-derived content.
"""

from __future__ import annotations

from .clarify import CLARIFY_SYSTEM_PROMPT
from .explain import EXPLAIN_SYSTEM_PROMPT
from .intake import INTAKE_SYSTEM_PROMPT
from .rank import RANK_SYSTEM_PROMPT

__all__ = [
    "CLARIFY_SYSTEM_PROMPT",
    "EXPLAIN_SYSTEM_PROMPT",
    "INTAKE_SYSTEM_PROMPT",
    "RANK_SYSTEM_PROMPT",
]
