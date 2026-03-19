"""Tests for storage.supabase_provider (mocked Supabase client)."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from get_store_url_and_tags.models import Product
from get_store_url_and_tags.storage.supabase_provider import SupabaseStorageProvider


def test_supabase_upsert_no_item_link_raises() -> None:
    @dataclass
    class BadItem:
        name: str
    bad = BadItem(name="x")
    with patch.object(SupabaseStorageProvider, "_ensure_client"):
        provider = SupabaseStorageProvider(url="https://fake.supabase.co", key="fake-key")
        provider._client = None
        with patch("get_store_url_and_tags.storage.supabase_provider.item_to_dict", return_value={}):
            with pytest.raises(ValueError, match="item_link"):
                provider.upsert(bad)


def test_supabase_upsert_calls_rpc(sample_product: Product) -> None:
    mock_rpc = MagicMock()
    mock_execute = MagicMock()
    mock_rpc.return_value.execute = mock_execute

    mock_client = MagicMock()
    mock_client.rpc = mock_rpc

    with patch.object(SupabaseStorageProvider, "_ensure_client"):
        provider = SupabaseStorageProvider(url="https://fake.supabase.co", key="fake-key")
        provider._client = mock_client

        provider.upsert(sample_product)

        mock_rpc.assert_called_once()
        assert mock_rpc.call_args[0][0] == "upsert_product_from_json"
        call_payload = mock_rpc.call_args[0][1]
        assert call_payload["p"]["item_link"] == sample_product.item_link
        assert call_payload["p"]["store"] == sample_product.store
        assert call_payload["p"]["tags"] == sample_product.tags
        mock_execute.assert_called_once()


def test_supabase_get_by_url_found(sample_product: Product) -> None:
    mock_execute = MagicMock()
    mock_execute.return_value = MagicMock(data=[{"item_link": sample_product.item_link, "item_name": sample_product.item_name}])
    mock_limit = MagicMock()
    mock_limit.execute = mock_execute
    mock_eq = MagicMock()
    mock_eq.limit.return_value = mock_limit
    mock_select = MagicMock()
    mock_select.eq.return_value = mock_eq
    mock_from = MagicMock()
    # Provider calls: client.from_("products_with_tags").select("*")...
    # So we must stub on the callable's return_value.
    mock_from.return_value.select.return_value = mock_select

    mock_client = MagicMock()
    mock_client.from_ = mock_from

    with patch.object(SupabaseStorageProvider, "_ensure_client"):
        provider = SupabaseStorageProvider(url="https://fake.supabase.co", key="fake-key")
        provider._client = mock_client

        result = provider.get_by_url(sample_product.item_link)

        assert result is not None
        assert result["item_link"] == sample_product.item_link
        mock_from.assert_called_once_with("products_with_tags")
        mock_from.return_value.select.assert_called_once_with("*")
        mock_eq.limit.assert_called_once_with(1)


def test_supabase_get_by_url_not_found() -> None:
    mock_execute = MagicMock()
    mock_execute.return_value = MagicMock(data=[])
    mock_limit = MagicMock()
    mock_limit.execute = mock_execute
    mock_eq = MagicMock()
    mock_eq.limit.return_value = mock_limit
    mock_select = MagicMock()
    mock_select.eq.return_value = mock_eq
    mock_from = MagicMock()
    # Provider calls: client.from_("products_with_tags").select("*")...
    # So we must stub on the callable's return_value.
    mock_from.return_value.select.return_value = mock_select

    mock_client = MagicMock()
    mock_client.from_ = mock_from

    with patch.object(SupabaseStorageProvider, "_ensure_client"):
        provider = SupabaseStorageProvider(url="https://fake.supabase.co", key="fake-key")
        provider._client = mock_client

        assert provider.get_by_url("https://example.com/missing") is None
