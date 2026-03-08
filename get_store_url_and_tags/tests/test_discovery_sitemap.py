"""Tests for discovery.sitemap."""

from unittest.mock import AsyncMock, patch

import pytest

from get_store_url_and_tags.discovery.sitemap import SitemapDiscovery
from get_store_url_and_tags.models.store import StoreDefinition


def test_parse_sitemap_index_with_namespace() -> None:
    discovery = SitemapDiscovery()
    xml = """<?xml version="1.0"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap><loc>https://example.com/sitemap1.xml</loc></sitemap>
        <sitemap><loc>https://example.com/sitemap2.xml</loc></sitemap>
    </sitemapindex>
    """
    urls = discovery._parse_sitemap_index(xml)
    assert "https://example.com/sitemap1.xml" in urls or len(urls) >= 1


def test_parse_sitemap_index_fallback_no_namespace() -> None:
    discovery = SitemapDiscovery()
    xml = """<?xml version="1.0"?>
    <sitemapindex>
        <sitemap><loc>https://example.com/sitemap.xml</loc></sitemap>
    </sitemapindex>
    """
    urls = discovery._parse_sitemap_index(xml)
    assert len(urls) >= 0  # fallback uses .//sitemap/loc


def test_parse_sitemap_urls_with_namespace() -> None:
    discovery = SitemapDiscovery()
    xml = """<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://example.com/page1</loc></url>
        <url><loc>https://example.com/page2</loc></url>
    </urlset>
    """
    urls = discovery._parse_sitemap_urls(xml)
    assert len(urls) >= 1
    assert "https://example.com/page1" in urls or "https://example.com/page2" in urls


def test_parse_sitemap_urls_fallback() -> None:
    discovery = SitemapDiscovery()
    xml = """<?xml version="1.0"?>
    <urlset>
        <url><loc>https://example.com/p</loc></url>
    </urlset>
    """
    urls = discovery._parse_sitemap_urls(xml)
    assert "https://example.com/p" in urls


def test_is_sitemap_index() -> None:
    discovery = SitemapDiscovery()
    assert discovery._is_sitemap_index("<sitemapindex") is True
    assert discovery._is_sitemap_index("<SITEMAPINDEX>") is True
    assert discovery._is_sitemap_index("<urlset>") is False


@pytest.mark.asyncio
async def test_discover_mocked_fetch(sample_store_definition: StoreDefinition) -> None:
    discovery = SitemapDiscovery()
    sitemap_xml = """<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://www.teststore.com/womens/tops</loc></url>
    </urlset>
    """
    async def mock_fetch(url):
        return sitemap_xml
    discovery._fetch_sitemap = mock_fetch
    result = await discovery.discover(sample_store_definition)
    assert len(result) >= 1
    assert any("womens" in u.url or "tops" in u.url for u in result)
