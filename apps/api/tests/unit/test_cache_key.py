"""Cache-key normalization yields identical keys for equivalent requests."""

from __future__ import annotations

from fragwise_api.search.cache import cache_key
from fragwise_api.search.schemas import FilterSpec, SearchRequest


def test_filter_order_does_not_affect_key() -> None:
    a = SearchRequest(
        query="Aventus",
        filters=FilterSpec(accord=["smoky", "fruity"]),
        top_k=20,
    )
    b = SearchRequest(
        query="  aventus  ",
        filters=FilterSpec(accord=["fruity", "smoky"]),
        top_k=20,
    )
    assert cache_key(a) == cache_key(b)


def test_query_case_and_whitespace_normalized() -> None:
    a = SearchRequest(query="Smoky Leather", top_k=10)
    b = SearchRequest(query="smoky leather", top_k=10)
    c = SearchRequest(query="  smoky leather  ", top_k=10)
    assert cache_key(a) == cache_key(b) == cache_key(c)


def test_top_k_distinguishes_keys() -> None:
    a = SearchRequest(query="x", top_k=5)
    b = SearchRequest(query="x", top_k=10)
    assert cache_key(a) != cache_key(b)


def test_include_order_does_not_affect_key() -> None:
    a = SearchRequest(query="x", include=["notes", "brand"])
    b = SearchRequest(query="x", include=["brand", "notes"])
    assert cache_key(a) == cache_key(b)


def test_namespace_prefix_present() -> None:
    key = cache_key(SearchRequest(query="x"))
    assert key.startswith("search:v1:")
