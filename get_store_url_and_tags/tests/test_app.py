"""Tests for app."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from datetime import datetime, timedelta, timezone

from get_store_url_and_tags.app import (
    PipelineOptions,
    PipelineResult,
    _get_storage_provider,
    run_pipeline,
)
from get_store_url_and_tags.config import Config
from get_store_url_and_tags.models import Product, StoreLink
from get_store_url_and_tags.models.store import StoreDefinition
from get_store_url_and_tags.config import Settings


def _make_config() -> Config:
    store = StoreDefinition(
        name="TestStore",
        homepage="https://www.teststore.com",
        domain="teststore.com",
    )
    return Config(stores=[store], settings=Settings())


def test_pipeline_options_defaults() -> None:
    opts = PipelineOptions()
    assert opts.stores_filter is None
    assert opts.headless is True
    assert opts.dump_urls is False
    assert opts.disable_fetch_clothing_items is False
    assert opts.category is None
    assert opts.store_in_database is False
    assert opts.delete_stale_items_days is None


def test_pipeline_result_success() -> None:
    r = PipelineResult(entries=[], products=None)
    assert r.success is True


def test_get_storage_provider_returns_supabase_by_default() -> None:
    with patch.dict("os.environ", {"STORAGE_BACKEND": ""}, clear=False):
        provider = _get_storage_provider()
    from get_store_url_and_tags.storage import SupabaseStorageProvider
    assert isinstance(provider, SupabaseStorageProvider)


def test_get_storage_provider_returns_firestore_when_explicit() -> None:
    with patch.dict("os.environ", {"STORAGE_BACKEND": "firestore"}, clear=False):
        provider = _get_storage_provider()
    from get_store_url_and_tags.storage import FirestoreStorageProvider
    assert isinstance(provider, FirestoreStorageProvider)


def test_get_storage_provider_returns_supabase_when_configured() -> None:
    with patch.dict(
        "os.environ",
        {
            "STORAGE_BACKEND": "supabase",
            "SUPABASE_URL": "https://x.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "secret",
        },
        clear=False,
    ):
        provider = _get_storage_provider()
    from get_store_url_and_tags.storage import SupabaseStorageProvider
    assert isinstance(provider, SupabaseStorageProvider)


@pytest.mark.asyncio
async def test_run_pipeline_returns_entries_and_products() -> None:
    config = _make_config()
    options = PipelineOptions(
        stores_filter=["TestStore"],
        disable_fetch_clothing_items=False,
        debug_dir=Path("/tmp/test_debug"),
    )
    link = StoreLink(name="TestStore", url="https://test.com/cat", tags=["Womens"])
    product = Product(
        store="TestStore",
        item_name="P",
        item_image_links=[],
        item_link="https://test.com/p/1",
        price="$10",
        tags=[],
    )
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[link])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        with patch("get_store_url_and_tags.scraping.orchestrator.ScrapingOrchestrator") as mock_scrape_class:
            mock_scrape = MagicMock()
            mock_scrape.run = AsyncMock(return_value=[product])
            mock_scrape_class.return_value = mock_scrape
            result = await run_pipeline(config, options)
    assert len(result.entries) == 1
    assert result.entries[0].url == link.url
    assert result.products is not None
    assert len(result.products) == 1
    assert result.products[0].item_name == "P"


@pytest.mark.asyncio
async def test_run_pipeline_category_filter() -> None:
    config = _make_config()
    options = PipelineOptions(
        stores_filter=["TestStore"],
        category="Womens/Tops",
        disable_fetch_clothing_items=True,
        debug_dir=Path("/tmp/test_debug"),
    )
    matching = StoreLink(name="TestStore", url="https://test.com/w/tops", tags=["Womens", "Tops"])
    non_matching = StoreLink(name="TestStore", url="https://test.com/m/jeans", tags=["Mens", "Jeans"])
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[matching, non_matching])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        result = await run_pipeline(config, options)
    assert len(result.entries) == 1
    assert result.entries[0].tags == ["Womens", "Tops"]


@pytest.mark.asyncio
async def test_run_pipeline_category_filter_prefix_and_single_segment() -> None:
    """Partial path matches longer tag paths; one segment matches anywhere in the list."""
    config = _make_config()
    options = PipelineOptions(
        stores_filter=["TestStore"],
        category="Womens/Bottoms",
        disable_fetch_clothing_items=True,
        debug_dir=Path("/tmp/test_debug"),
    )
    exact = StoreLink(name="TestStore", url="https://test.com/w/b", tags=["Womens", "Bottoms"])
    child = StoreLink(
        name="TestStore",
        url="https://test.com/w/b/j",
        tags=["Womens", "Bottoms", "Jeans"],
    )
    other = StoreLink(name="TestStore", url="https://test.com/m/j", tags=["Mens", "Jeans"])
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[exact, child, other])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        result = await run_pipeline(config, options)
    assert len(result.entries) == 2
    urls = {e.url for e in result.entries}
    assert urls == {exact.url, child.url}


@pytest.mark.asyncio
async def test_run_pipeline_category_filter_new_arrivals_segment() -> None:
    config = _make_config()
    options = PipelineOptions(
        stores_filter=["TestStore"],
        category="New Arrivals",
        disable_fetch_clothing_items=True,
        debug_dir=Path("/tmp/test_debug"),
    )
    na_branch = StoreLink(
        name="TestStore",
        url="https://test.com/new/w/bottoms",
        tags=["Womens", "Bottoms", "New Arrivals"],
    )
    no_na = StoreLink(
        name="TestStore",
        url="https://test.com/w/bottoms",
        tags=["Womens", "Bottoms"],
    )
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[na_branch, no_na])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        result = await run_pipeline(config, options)
    assert len(result.entries) == 1
    assert result.entries[0].url == na_branch.url


@pytest.mark.asyncio
async def test_run_pipeline_category_no_match_raises() -> None:
    config = _make_config()
    options = PipelineOptions(
        stores_filter=["TestStore"],
        category="Womens/Nonexistent",
        disable_fetch_clothing_items=True,
        debug_dir=Path("/tmp/test_debug"),
    )
    link = StoreLink(name="TestStore", url="https://test.com/cat", tags=["Womens", "Tops"])
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[link])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        with pytest.raises(ValueError, match="Category .* not found"):
            await run_pipeline(config, options)


@pytest.mark.asyncio
async def test_run_pipeline_disable_fetch_no_scraping() -> None:
    config = _make_config()
    options = PipelineOptions(
        stores_filter=["TestStore"],
        disable_fetch_clothing_items=True,
        debug_dir=Path("/tmp/test_debug"),
    )
    link = StoreLink(name="TestStore", url="https://test.com/cat", tags=["Womens"])
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[link])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        result = await run_pipeline(config, options)
    assert result.products is None


@pytest.mark.asyncio
async def test_run_pipeline_store_in_database_calls_upsert(tmp_path: Path) -> None:
    config = _make_config()
    product = Product(
        store="TestStore",
        item_name="P",
        item_image_links=[],
        item_link="https://test.com/p/1",
        price="$10",
        tags=[],
    )
    options = PipelineOptions(
        stores_filter=["TestStore"],
        disable_fetch_clothing_items=False,
        store_in_database=True,
        debug_dir=tmp_path,
    )
    link = StoreLink(name="TestStore", url="https://test.com/cat", tags=["Womens"])
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[link])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        with patch("get_store_url_and_tags.scraping.orchestrator.ScrapingOrchestrator") as mock_scrape_class:
            mock_scrape = MagicMock()
            mock_scrape.run = AsyncMock(return_value=[product])
            mock_scrape_class.return_value = mock_scrape
            with patch("get_store_url_and_tags.app._get_storage_provider") as mock_get_storage:
                mock_provider = MagicMock()
                mock_get_storage.return_value = mock_provider
                await run_pipeline(config, options)
    mock_provider.upsert.assert_called_once_with(product)


@pytest.mark.asyncio
async def test_run_pipeline_delete_stale_items_calls_provider(tmp_path: Path) -> None:
    config = _make_config()
    options = PipelineOptions(
        stores_filter=["TestStore"],
        disable_fetch_clothing_items=True,
        delete_stale_items_days=7,
        debug_dir=tmp_path,
    )
    link = StoreLink(name="TestStore", url="https://test.com/cat", tags=["Womens"])
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[link])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        with patch("get_store_url_and_tags.app._get_storage_provider") as mock_get_storage:
            mock_provider = MagicMock()
            mock_provider.delete_items_not_updated_since.return_value = 3
            mock_get_storage.return_value = mock_provider
            await run_pipeline(config, options)

    mock_provider.delete_items_not_updated_since.assert_called_once()
    assert mock_provider.delete_items_not_updated_since.call_args.kwargs["store_names"] == [
        "TestStore"
    ]
    cutoff = mock_provider.delete_items_not_updated_since.call_args.args[0]

    delta = datetime.now(timezone.utc) - cutoff
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, minutes=5)


@pytest.mark.asyncio
async def test_run_pipeline_delete_stale_items_no_store_scope(tmp_path: Path) -> None:
    config = _make_config()
    options = PipelineOptions(
        stores_filter=None,
        disable_fetch_clothing_items=True,
        delete_stale_items_days=1,
        debug_dir=tmp_path,
    )
    link = StoreLink(name="TestStore", url="https://test.com/cat", tags=["Womens"])
    with patch("get_store_url_and_tags.app.DiscoveryOrchestrator") as mock_orch_class:
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value=[link])
        mock_orch.close = AsyncMock()
        mock_orch_class.return_value = mock_orch
        with patch("get_store_url_and_tags.app._get_storage_provider") as mock_get_storage:
            mock_provider = MagicMock()
            mock_provider.delete_items_not_updated_since.return_value = 0
            mock_get_storage.return_value = mock_provider
            await run_pipeline(config, options)

    assert mock_provider.delete_items_not_updated_since.call_args.kwargs["store_names"] is None
