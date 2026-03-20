"""Tests for scraping.base."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from get_store_url_and_tags.models import Product
from get_store_url_and_tags.scraping.base import BaseScraper


class ConcreteScraper(BaseScraper):
    def parse_html(self, soup: BeautifulSoup, tags: list) -> list:
        return [
            Product(
                store=self.store_name,
                item_name="Test",
                item_image_links=[],
                item_link="https://example.com/1",
                price="$10",
                tags=tags,
            )
        ]


def test_base_scraper_content_ready_selector() -> None:
    s = BaseScraper(store_name="X")
    assert s.content_ready_selector() is None


def test_base_scraper_parse_html_not_implemented() -> None:
    s = BaseScraper(store_name="X")
    soup = BeautifulSoup("<html></html>", "html.parser")
    with pytest.raises(NotImplementedError):
        s.parse_html(soup, [])


@pytest.mark.asyncio
async def test_scrape_returns_products_from_parse_html() -> None:
    scraper = ConcreteScraper(store_name="TestStore")
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body></body></html>")
    mock_page.mouse.wheel = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await scraper.scrape(mock_page, "https://example.com", ["Tops"])
    assert len(result) == 1
    assert result[0].item_name == "Test"
    assert result[0].tags == ["Tops"]


@pytest.mark.asyncio
async def test_scrape_exception_returns_empty() -> None:
    scraper = ConcreteScraper(store_name="TestStore")
    mock_page = MagicMock()
    mock_page.goto = AsyncMock(side_effect=Exception("network error"))
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await scraper.scrape(mock_page, "https://example.com", [])
    assert result == []
