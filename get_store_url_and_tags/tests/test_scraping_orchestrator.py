"""Tests for scraping.orchestrator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from get_store_url_and_tags.models import Product, StoreLink
from get_store_url_and_tags.scraping.orchestrator import ScrapingOrchestrator


@pytest.mark.asyncio
async def test_run_empty_entries() -> None:
    orch = ScrapingOrchestrator(headless=True)
    result = await orch.run([], sequential=True)
    assert result == []


@pytest.mark.asyncio
async def test_run_max_urls_per_shop() -> None:
    entries = [
        StoreLink(name="StoreA", url="https://a.com/1", tags=[]),
        StoreLink(name="StoreA", url="https://a.com/2", tags=[]),
        StoreLink(name="StoreA", url="https://a.com/3", tags=[]),
    ]
    product = Product(
        store="StoreA",
        item_name="P",
        item_image_links=[],
        item_link="https://a.com/p/1",
        price="$10",
        tags=[],
    )
    mock_scraper = MagicMock()
    mock_scraper.scrape = AsyncMock(return_value=[product])
    mock_page = MagicMock()
    mock_page.add_init_script = AsyncMock()
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    mock_p = MagicMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_p)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    with patch("get_store_url_and_tags.scraping.orchestrator.async_playwright", return_value=mock_playwright):
        with patch("get_store_url_and_tags.scraping.orchestrator.get_scraper_for_store", return_value=mock_scraper):
            orch = ScrapingOrchestrator(headless=True)
            result = await orch.run(entries, max_urls_per_shop=2, sequential=True)
    assert len(result) == 2
    assert mock_scraper.scrape.call_count == 2


@pytest.mark.asyncio
async def test_run_sequential(sample_store_link, sample_product) -> None:
    entries = [sample_store_link]
    mock_scraper = MagicMock()
    mock_scraper.scrape = AsyncMock(return_value=[sample_product])
    mock_page = MagicMock()
    mock_page.add_init_script = AsyncMock()
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    mock_p = MagicMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_p)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    with patch("get_store_url_and_tags.scraping.orchestrator.async_playwright", return_value=mock_playwright):
        with patch("get_store_url_and_tags.scraping.orchestrator.get_scraper_for_store", return_value=mock_scraper):
            orch = ScrapingOrchestrator(headless=True)
            result = await orch.run(entries, sequential=True)
    assert len(result) == 1
    assert result[0].item_name == sample_product.item_name


@pytest.mark.asyncio
async def test_run_no_scraper_for_store() -> None:
    entries = [StoreLink(name="UnknownStore", url="https://x.com/cat", tags=[])]
    mock_page = MagicMock()
    mock_page.add_init_script = AsyncMock()
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    mock_p = MagicMock()
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright = MagicMock()
    mock_playwright.__aenter__ = AsyncMock(return_value=mock_p)
    mock_playwright.__aexit__ = AsyncMock(return_value=None)
    with patch("get_store_url_and_tags.scraping.orchestrator.async_playwright", return_value=mock_playwright):
        with patch("get_store_url_and_tags.scraping.orchestrator.get_scraper_for_store", return_value=None):
            orch = ScrapingOrchestrator(headless=True)
            result = await orch.run(entries, sequential=True)
    assert result == []
