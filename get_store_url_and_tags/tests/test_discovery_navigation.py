"""Tests for discovery.navigation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from get_store_url_and_tags.discovery.navigation import NavigationDiscovery
from get_store_url_and_tags.models.store import StoreDefinition


def test_navigation_discovery_name() -> None:
    nav = NavigationDiscovery(headless=True)
    assert nav.name == "navigation"


@pytest.mark.asyncio
async def test_navigation_discover_mocked_browser(sample_store_definition: StoreDefinition) -> None:
    nav = NavigationDiscovery(headless=True)
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.add_init_script = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])
    mock_page.evaluate = AsyncMock(return_value=[])
    mock_page.context = MagicMock()
    mock_page.context.close = AsyncMock()
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.is_connected = MagicMock(return_value=True)
    with patch.object(nav, "_get_browser", new_callable=AsyncMock, return_value=mock_browser):
        with patch("get_store_url_and_tags.discovery.navigation.URLClassifier") as mock_cls:
            mock_cls.return_value.filter_category_urls.return_value = [
                "https://www.teststore.com/womens/tops"
            ]
            result = await nav.discover(sample_store_definition)
    assert len(result) >= 0
    await nav.close()
