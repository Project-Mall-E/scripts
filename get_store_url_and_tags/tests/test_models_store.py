"""Tests for models.store."""

import pytest

from get_store_url_and_tags.models.store import StoreDefinition


def test_store_definition_construction() -> None:
    store = StoreDefinition(
        name="Abercrombie",
        homepage="https://www.abercrombie.com",
        domain="abercrombie.com",
        discovery_strategy="sitemap",
        extra_category_patterns=[r"/extra/"],
        extra_exclude_patterns=[r"/exclude/"],
        max_path_depth=3,
    )
    assert store.name == "Abercrombie"
    assert store.homepage == "https://www.abercrombie.com"
    assert store.domain == "abercrombie.com"
    assert store.discovery_strategy == "sitemap"
    assert store.extra_category_patterns == [r"/extra/"]
    assert store.extra_exclude_patterns == [r"/exclude/"]
    assert store.max_path_depth == 3


def test_store_definition_defaults() -> None:
    store = StoreDefinition(
        name="Test",
        homepage="https://test.com",
        domain="test.com",
    )
    assert store.discovery_strategy == "auto"
    assert store.extra_category_patterns == []
    assert store.extra_exclude_patterns == []
    assert store.max_path_depth is None
