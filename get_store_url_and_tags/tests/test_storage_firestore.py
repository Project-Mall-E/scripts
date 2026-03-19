"""Tests for storage.firestore_provider (helpers + mocked Firestore)."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from get_store_url_and_tags.models import Product
from get_store_url_and_tags.storage.common import item_to_dict
from get_store_url_and_tags.storage.firestore_provider import (
    FirestoreStorageProvider,
    _document_id_to_url,
    _url_to_document_id,
)


def test_url_to_document_id_roundtrip() -> None:
    url = "https://example.com/p/product-1"
    doc_id = _url_to_document_id(url)
    assert isinstance(doc_id, str)
    assert doc_id.isascii()
    decoded = _document_id_to_url(doc_id)
    assert decoded == url


def test_document_id_to_url() -> None:
    url = "https://test.com/a"
    doc_id = _url_to_document_id(url)
    assert _document_id_to_url(doc_id) == url


def test_item_to_dict_dataclass(sample_product: Product) -> None:
    d = item_to_dict(sample_product)
    assert isinstance(d, dict)
    assert d["item_link"] == sample_product.item_link
    assert d["store"] == sample_product.store


def test_item_to_dict_dict() -> None:
    d = item_to_dict({"item_link": "https://x.com/1", "name": "Y"})
    assert d == {"item_link": "https://x.com/1", "name": "Y"}


def test_item_to_dict_invalid_type() -> None:
    with pytest.raises(TypeError, match="dataclass instance or dict"):
        item_to_dict("not a dict or dataclass")


def test_firestore_upsert_no_item_link_raises() -> None:
    @dataclass
    class BadItem:
        name: str
    bad = BadItem(name="x")
    with patch.object(FirestoreStorageProvider, "_ensure_client"):
        provider = FirestoreStorageProvider(credentials_path="/nonexistent/path.json")
        provider._client = None
        provider._collection = None
        with patch("get_store_url_and_tags.storage.firestore_provider.item_to_dict", return_value={}):
            with pytest.raises(ValueError, match="item_link"):
                provider.upsert(bad)


def test_firestore_upsert_new_doc(sample_product: Product) -> None:
    mock_doc_ref = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.exists = False
    mock_doc_ref.get.return_value = mock_snapshot

    mock_collection = MagicMock()
    mock_collection.document.return_value = mock_doc_ref

    with patch.object(FirestoreStorageProvider, "_ensure_client"):
        provider = FirestoreStorageProvider(credentials_path="/fake/path.json")
        provider._client = MagicMock()
        provider._collection = mock_collection

        provider.upsert(sample_product)

        mock_doc_ref.set.assert_called_once()
        payload = mock_doc_ref.set.call_args[0][0]
        assert payload["item_link"] == sample_product.item_link
        assert "inserted_time" in payload
        assert "updated_time" in payload


def test_firestore_upsert_existing_doc(sample_product: Product) -> None:
    mock_doc_ref = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_doc_ref.get.return_value = mock_snapshot

    mock_collection = MagicMock()
    mock_collection.document.return_value = mock_doc_ref

    with patch.object(FirestoreStorageProvider, "_ensure_client"):
        provider = FirestoreStorageProvider(credentials_path="/fake/path.json")
        provider._client = MagicMock()
        provider._collection = mock_collection

        provider.upsert(sample_product)

        mock_doc_ref.update.assert_called_once()
        payload = mock_doc_ref.update.call_args[0][0]
        assert "updated_time" in payload


def test_firestore_get_by_url_found(sample_product: Product) -> None:
    mock_doc_ref = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {"item_link": sample_product.item_link, "item_name": sample_product.item_name}
    mock_doc_ref.get.return_value = mock_snapshot

    mock_collection = MagicMock()
    mock_collection.document.return_value = mock_doc_ref

    with patch.object(FirestoreStorageProvider, "_ensure_client"):
        provider = FirestoreStorageProvider(credentials_path="/fake/path.json")
        provider._client = MagicMock()
        provider._collection = mock_collection

        result = provider.get_by_url(sample_product.item_link)
        assert result is not None
        assert result["item_link"] == sample_product.item_link


def test_firestore_get_by_url_not_found() -> None:
    mock_doc_ref = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.exists = False
    mock_doc_ref.get.return_value = mock_snapshot

    mock_collection = MagicMock()
    mock_collection.document.return_value = mock_doc_ref

    with patch.object(FirestoreStorageProvider, "_ensure_client"):
        provider = FirestoreStorageProvider(credentials_path="/fake/path.json")
        provider._client = MagicMock()
        provider._collection = mock_collection

        assert provider.get_by_url("https://example.com/missing") is None
