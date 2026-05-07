"""Shared constants for hybrid search.

ADR-0031: this module is the single source of truth for embedding-model
identity. Both the indexer (`data/scripts/embed_fragrances.py`) and the
query-time embedder (`fragwise_api.search.embedder`) import from here so
that drift between index time and query time is impossible without a
deliberate edit. A unit test asserts byte-for-byte equality between the
two import sites.
"""

from __future__ import annotations

# Embedding model identity. Bump deliberately and re-embed the catalog.
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 512
EMBEDDING_VIEW = "combined"

# RRF fusion constant (per pgvector cookbook + Microsoft RRF paper).
RRF_K = 60

# pgvector HNSW runtime tuning. Trades a small latency cost for materially
# higher recall@K vs the default of 40 on catalogs in the 10K-50K row range.
DEFAULT_HNSW_EF_SEARCH = 100

# top_k clamps for the search request schema.
DEFAULT_TOP_K = 20
MAX_TOP_K = 50

# Cache namespace + TTL.
CACHE_NAMESPACE = "search:v1"
CACHE_TTL_SECONDS = 86400  # 24h
