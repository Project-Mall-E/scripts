"""Tests for discovery.link_crawler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from get_store_url_and_tags.discovery.link_crawler import LinkCrawlerDiscovery
from get_store_url_and_tags.models.store import StoreDefinition


def test_link_crawler_name() -> None:
    crawler = LinkCrawlerDiscovery(max_depth=2)
    assert crawler.name == "link_crawler"


def test_is_same_domain() -> None:
    crawler = LinkCrawlerDiscovery(max_depth=2)
    assert crawler._is_same_domain("https://example.com/path", "example.com") is True
    assert crawler._is_same_domain("https://sub.example.com/path", "example.com") is True
    assert crawler._is_same_domain("https://other.com/path", "example.com") is False


@pytest.mark.asyncio
async def test_link_crawler_discover_mocked() -> None:
    store = StoreDefinition(
        name="TestStore",
        homepage="https://www.teststore.com",
        domain="teststore.com",
    )
    crawler = LinkCrawlerDiscovery(max_depth=1)
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.add_init_script = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])
    mock_page.content = AsyncMock(return_value="<html></html>")
    mock_page.context = MagicMock()
    mock_page.context.close = AsyncMock()
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.is_connected = MagicMock(return_value=True)
    with patch.object(crawler, "_get_browser", new_callable=AsyncMock, return_value=mock_browser):
        with patch.object(crawler.rate_limiter, "acquire", new_callable=AsyncMock):
            with patch.object(crawler.robots_checker, "is_allowed", new_callable=AsyncMock, return_value=True):
                result = await crawler.discover(store)
    assert isinstance(result, list)
    await crawler.close()
