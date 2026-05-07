"""ADR-0031: parity between query-time embedder and offline indexer.

If either side bumps the model or dim count without the other, this test
fails loudly so the catalog never goes out of sync with the query path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `data/scripts` importable so we can directly import the indexer.
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "data" / "scripts"))


def test_embedding_model_and_dims_match_indexer() -> None:
    from fragwise_api.search import constants as q

    embed_fragrances = pytest.importorskip("embed_fragrances")

    assert embed_fragrances.MODEL == q.EMBEDDING_MODEL
    assert embed_fragrances.DIMENSIONS == q.EMBEDDING_DIMENSIONS
    assert embed_fragrances.VIEW == q.EMBEDDING_VIEW
