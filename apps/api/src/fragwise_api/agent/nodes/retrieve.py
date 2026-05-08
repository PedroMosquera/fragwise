"""Retrieve node — thin in-process wrapper around `hybrid_retrieve`.

ADR-0033: NO HTTP loopback. Imports `hybrid_retrieve` directly. Mirrors P2
degraded-mode (catch APIError -> FTS fallback). Embedding constants come
from `search/constants.py` (agent spec: Embedding Parity).

Imports of `fragwise_api.search.*` are deferred to function-call time to
avoid an import-order cycle between `search.schemas` (which references
`FragranceListItem` from the catalog package) and the catalog package
(whose router imports `search.router`).
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from openai import APIConnectionError, APIError, APITimeoutError
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from fragwise_api.db.models import Fragrance
from fragwise_api.search.constants import (
    EMBEDDING_DIMENSIONS,  # noqa: F401  (re-exported for spec parity check)
    EMBEDDING_MODEL,  # noqa: F401  (re-exported for spec parity check)
)

from ..constants import RETRIEVE_TOP_K
from ..state import FragranceCandidate, State

_GENDER_MAP: dict[str, str] = {
    "masculine": "masculine",
    "feminine": "feminine",
    "unisex": "unisex",
    # Tolerate the DB-internal abbreviations if a caller round-trips them.
    "masc": "masculine",
    "fem": "feminine",
}


def _query_text(prefs: dict[str, Any]) -> str:
    """Build a retrieval query string from structured preferences."""
    parts: list[str] = []
    for k in ("families", "occasion", "season", "intensity"):
        v = prefs.get(k)
        if isinstance(v, list):
            parts.extend(str(x) for x in v if x)
        elif v:
            parts.append(str(v))
    return " ".join(parts).strip() or "fragrance"


def _filter_spec(prefs: dict[str, Any]) -> Any:
    """Build a `search.schemas.FilterSpec` from extracted preferences.

    Imported lazily to avoid the import-time cycle described in the module
    docstring.
    """
    from fragwise_api.search.schemas import FilterSpec

    gender_raw = prefs.get("gender")
    gender_str = _GENDER_MAP.get(gender_raw) if isinstance(gender_raw, str) else None
    families = prefs.get("families") or []
    accord = [str(x) for x in families if isinstance(x, str)]
    # FilterSpec.gender is `Literal["masculine","feminine","unisex"] | None`;
    # `_GENDER_MAP` only ever yields one of those strings or `None`, but
    # mypy can't infer that from a generic-dict lookup — use `model_validate`
    # for a runtime check that satisfies both invariants.
    return FilterSpec.model_validate({"gender": gender_str, "accord": accord})


async def retrieve_node(state: State, config: RunnableConfig) -> dict[str, Any]:
    # Deferred imports (see module docstring for the cycle this avoids).
    from fragwise_api.search.embedder import embed_query
    from fragwise_api.search.fallback import fts_only_retrieval
    from fragwise_api.search.retrieval import hybrid_retrieve

    prefs = state.get("preferences") or {}
    cfg = config.get("configurable") or {}
    sm = cfg["db_sessionmaker"]
    openai_client = cfg["openai_client"]
    qtext = _query_text(prefs)
    filters = _filter_spec(prefs)
    degraded = bool(state.get("degraded", False))
    embed_failed = False

    async with sm() as session:
        rows: list[Any]
        try:
            embedding = await embed_query(qtext, openai_client)
            rows = await hybrid_retrieve(
                session,
                query_embedding=embedding,
                query_text=qtext,
                filters=filters,
                top_k=RETRIEVE_TOP_K,
            )
        except (APIError, APITimeoutError, APIConnectionError):
            embed_failed = True
            degraded = True
            rows = await fts_only_retrieval(
                session,
                query_text=qtext,
                filters=filters,
                top_k=RETRIEVE_TOP_K,
            )

        ids = [r.fragrance_id for r in rows]
        if not ids:
            update: dict[str, Any] = {"candidates": [], "degraded": degraded}
            if embed_failed:
                update["error"] = "openai_embedding_failed"
                update["messages"] = [
                    AIMessage(
                        content="",
                        additional_kwargs={
                            "chat_event": "node_degraded",
                            "error": "openai_embedding_failed",
                        },
                    )
                ]
            return update
        stmt = select(Fragrance).where(Fragrance.id.in_(ids)).options(joinedload(Fragrance.brand))
        result = await session.execute(stmt)
        by_id = {f.id: f for f in result.scalars().unique().all()}

    candidates: list[FragranceCandidate] = []
    for r in rows:
        f = by_id.get(r.fragrance_id)
        if f is None:
            continue
        brand = getattr(f, "brand", None)
        candidates.append(
            FragranceCandidate(
                fragrance_id=r.fragrance_id,
                slug=f.slug,
                name=f.name,
                brand_slug=brand.slug if brand is not None else "",
                relevance_score=r.relevance_score,
                match_reason=list(r.match_reason),
            )
        )
    update = {"candidates": candidates, "degraded": degraded}
    if embed_failed:
        update["error"] = "openai_embedding_failed"
        update["messages"] = [
            AIMessage(
                content="",
                additional_kwargs={
                    "chat_event": "node_degraded",
                    "error": "openai_embedding_failed",
                },
            )
        ]
    return update
