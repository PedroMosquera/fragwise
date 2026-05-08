"""Tiered model identities and operator-tunable budget defaults.

Single source of truth — no node hardcodes a model string. Every constant is
env-overridable; defaults are sized for a free-tier-friendly project where
the daily kill-switch caps spend at ~$5-10/day.
"""

from __future__ import annotations

import os

# Tiered model identities (env-overridable per agent spec: Tiered Model Invariant).
MODEL_FAST: str = os.environ.get("FRAGWISE_CHAT_MODEL_MINI", "gpt-4o-mini")
MODEL_SMART: str = os.environ.get("FRAGWISE_CHAT_MODEL_PRO", "gpt-4o")

# Aliases per agent spec naming (MODEL_MINI / MODEL_PRO are the spec's names).
MODEL_MINI: str = MODEL_FAST
MODEL_PRO: str = MODEL_SMART

# tiktoken encoder model — gpt-4o-mini uses o200k_base (verified Context7 + ADR-0038).
ENCODER_MODEL: str = "gpt-4o-mini"

# Daily kill-switch — chat fans out to 3-5 LLM calls per turn, so the cap is
# tighter than search's 5000/d. 200 calls/day ~= $4-10/day at our model mix.
DAILY_CAP_DEFAULT: int = 200

# Per-IP slowapi limits. Each slot is one full chat turn. Chat is more
# expensive than search by an order of magnitude, hence the much tighter
# numbers vs search's 60/h.
PER_IP_HOUR: int = 5
PER_IP_DAY: int = 20

# Conversation cap (10 user-assistant pairs = 20 messages). Beyond this,
# 422; future "summarize-and-restart" UX may relax the cliff.
MAX_TURNS: int = 10
MAX_MESSAGES: int = MAX_TURNS * 2

# Per-message hard caps. Char-cap is a cheap pre-check before tokenizing
# (an attacker can't DoS tiktoken with megabyte payloads).
MAX_CHARS_PER_MESSAGE: int = 4000
MAX_TOKENS_PER_MESSAGE: int = 1000

# Per-LLM-call output caps to bound worst-case spend per turn.
MAX_TOKENS_INTAKE: int = 400
MAX_TOKENS_CLARIFY: int = 200
MAX_TOKENS_RANK: int = 400
MAX_TOKENS_EXPLAIN: int = 800

# Retrieve top-K and rank cutoff.
RETRIEVE_TOP_K: int = 10
RANK_SCORE_THRESHOLD: float = 0.3
PICK_COUNT_MIN: int = 3
PICK_COUNT_MAX: int = 5

# Required profile fields; clarify trips when 2+ are missing.
REQUIRED_PROFILE_FIELDS: tuple[str, ...] = (
    "gender",
    "occasion",
    "season",
    "intensity",
    "budget",
)
CLARIFY_MISSING_THRESHOLD: int = 2

# Intake skip threshold — too-short messages bypass the LLM call.
INTAKE_MIN_CHARS: int = 10
