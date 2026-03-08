"""Tests for storage.base using FakeStorageProvider."""

import pytest

from get_store_url_and_tags.models import Product
from get_store_url_and_tags.tests.conftest import FakeStorageProvider


def test_fake_storage_upsert_and_get_by_url(sample_product: Product) -> None:
    store = FakeStorageProvider()
    store.upsert(sample_product)
    retrieved = store.get_by_url(sample_product.item_link)
    assert retrieved is not None
    assert retrieved["item_link"] == sample_product.item_link
    assert retrieved["item_name"] == sample_product.item_name


def test_fake_storage_get_by_url_missing() -> None:
    store = FakeStorageProvider()
    assert store.get_by_url("https://example.com/nonexistent") is None


def test_fake_storage_upsert_dict() -> None:
    store = FakeStorageProvider()
    store.upsert({"item_link": "https://example.com/1", "item_name": "X"})
    assert store.get_by_url("https://example.com/1")["item_name"] == "X"


def test_fake_storage_upsert_no_item_link_raises() -> None:
    store = FakeStorageProvider()
    with pytest.raises(ValueError, match="item_link"):
        store.upsert({"name": "no link"})
