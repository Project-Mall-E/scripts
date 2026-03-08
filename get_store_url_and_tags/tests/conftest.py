"""Shared fixtures and fakes for get_store_url_and_tags tests."""

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pytest

from get_store_url_and_tags.models import (
    DiscoveredURL,
    Product,
    StoreDefinition,
    StoreLink,
)
from get_store_url_and_tags.storage.base import StorageProvider


@pytest.fixture
def sample_store_definition() -> StoreDefinition:
    return StoreDefinition(
        name="TestStore",
        homepage="https://www.teststore.com",
        domain="teststore.com",
        discovery_strategy="auto",
        extra_category_patterns=[],
        extra_exclude_patterns=[],
        max_path_depth=None,
    )


@pytest.fixture
def sample_discovered_url(sample_store_definition: StoreDefinition) -> DiscoveredURL:
    return DiscoveredURL(
        url="https://www.teststore.com/womens/tops",
        store_name=sample_store_definition.name,
        nav_text="Tops",
        page_title="Women's Tops",
        breadcrumb_text="Women / Tops",
        discovery_method="sitemap",
        depth=1,
    )


@pytest.fixture
def sample_store_link(sample_store_definition: StoreDefinition) -> StoreLink:
    return StoreLink(
        name=sample_store_definition.name,
        url="https://www.teststore.com/womens/tops",
        tags=["Womens", "Tops"],
    )


@pytest.fixture
def sample_product(sample_store_definition: StoreDefinition) -> Product:
    return Product(
        store=sample_store_definition.name,
        item_name="Test Shirt",
        item_image_link="https://www.teststore.com/img/shirt.jpg",
        item_link="https://www.teststore.com/p/shirt-1",
        price="$29.99",
        tags=["Womens", "Tops"],
    )


@pytest.fixture
def sample_config_json(tmp_path: Path) -> Path:
    """Minimal valid config JSON written to a temp file."""
    config = {
        "stores": [
            {
                "name": "TestStore",
                "homepage": "https://www.teststore.com",
                "domain": "teststore.com",
                "discovery_strategy": "auto",
            }
        ],
        "settings": {
            "rate_limit_seconds": 1.5,
            "rate_limit_jitter": 0.1,
            "max_retries": 3,
            "request_timeout_seconds": 30.0,
            "max_crawl_depth": 2,
            "scrape_page_wait_seconds": 2.5,
            "scrape_scroll_delay_seconds": 0.6,
            "scrape_scroll_count": 2,
            "navigation_wait_seconds": 1.5,
            "navigation_hover_delay_seconds": 0.2,
            "navigation_post_hover_seconds": 0.5,
            "link_crawler_post_goto_seconds": 0.5,
        },
    }
    path = tmp_path / "stores.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


class FakeStorageProvider(StorageProvider):
    """In-memory StorageProvider for tests."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def upsert(self, item: Any) -> None:
        data = item if isinstance(item, dict) else _asdict(item)
        url = data.get("item_link")
        if not url:
            raise ValueError("item must have an 'item_link' field")
        self._store[url] = data

    def get_by_url(self, url: str) -> Any | None:
        return self._store.get(url)


def _asdict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return dict(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError("item must be a dataclass instance or dict")
