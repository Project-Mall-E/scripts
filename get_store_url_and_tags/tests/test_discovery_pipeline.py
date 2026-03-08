"""Tests for discovery.pipeline."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from get_store_url_and_tags.discovery.pipeline import (
    deduplicate_urls,
    process,
    tag_urls,
)
from get_store_url_and_tags.models import DiscoveredURL, StoreLink
from get_store_url_and_tags.tagging.normalizer import TagNormalizer
from get_store_url_and_tags.tagging.rules import TagExtractor


def test_deduplicate_urls_empty() -> None:
    assert deduplicate_urls([]) == []


def test_deduplicate_urls_single() -> None:
    u = DiscoveredURL(url="https://a.com/p", store_name="S")
    result = deduplicate_urls([u])
    assert len(result) == 1
    assert result[0].url == "https://a.com/p"


def test_deduplicate_urls_same_url_trailing_slash() -> None:
    u1 = DiscoveredURL(url="https://a.com/p", store_name="S")
    u2 = DiscoveredURL(url="https://a.com/p/", store_name="S")
    result = deduplicate_urls([u1, u2])
    assert len(result) == 1


def test_deduplicate_urls_merge_richer_metadata() -> None:
    u1 = DiscoveredURL(
        url="https://a.com/p",
        store_name="S",
        nav_text=None,
        page_title=None,
        breadcrumb_text=None,
    )
    u2 = DiscoveredURL(
        url="https://a.com/p/",
        store_name="S",
        nav_text="Tops",
        page_title="Tops Page",
        breadcrumb_text="Home / Tops",
    )
    result = deduplicate_urls([u1, u2])
    assert len(result) == 1
    assert result[0].nav_text == "Tops"
    assert result[0].page_title == "Tops Page"
    assert result[0].breadcrumb_text == "Home / Tops"


def test_deduplicate_urls_no_merge_when_existing_richer() -> None:
    u1 = DiscoveredURL(
        url="https://a.com/p",
        store_name="S",
        nav_text="Tops",
        page_title="Tops",
        breadcrumb_text="Tops",
    )
    u2 = DiscoveredURL(url="https://a.com/p/", store_name="S")
    result = deduplicate_urls([u1, u2])
    assert len(result) == 1
    assert result[0].nav_text == "Tops"


def test_tag_urls_with_tags(sample_store_definition, sample_discovered_url) -> None:
    extractor = TagExtractor()
    normalizer = TagNormalizer()
    # sample_discovered_url has nav_text "Tops", page_title "Women's Tops" -> should match
    result = tag_urls([sample_discovered_url], extractor, normalizer)
    assert len(result) >= 1
    assert result[0].name == sample_store_definition.name
    assert result[0].url == sample_discovered_url.url
    assert result[0].tags


def test_tag_urls_no_tags_skipped(caplog: pytest.LogCaptureFixture) -> None:
    extractor = TagExtractor()
    normalizer = TagNormalizer()
    # URL with no matching keywords -> no tags
    u = DiscoveredURL(
        url="https://example.com/xyz-nomatch",
        store_name="S",
        nav_text="Xyz",
        page_title="Xyz",
    )
    result = tag_urls([u], extractor, normalizer)
    assert len(result) == 0
    assert "No tags extracted" in caplog.text


def test_tag_urls_mock_extractor_normalizer() -> None:
    extractor = MagicMock()
    extractor.extract.return_value = ["Womens", "Tops"]
    normalizer = MagicMock()
    normalizer.normalize.return_value = ["Womens", "Tops"]
    u = DiscoveredURL(url="https://a.com/p", store_name="S")
    result = tag_urls([u], extractor, normalizer)
    assert len(result) == 1
    assert result[0].tags == ["Womens", "Tops"]
    extractor.extract.assert_called_once()
    normalizer.normalize.assert_called_once_with(["Womens", "Tops"])


@pytest.mark.asyncio
async def test_process_empty() -> None:
    checker = AsyncMock()
    extractor = TagExtractor()
    normalizer = TagNormalizer()
    result = await process([], checker, extractor, normalizer)
    assert result == []
    checker.filter_allowed.assert_not_called()


@pytest.mark.asyncio
async def test_process_filter_dedupe_tag() -> None:
    u1 = DiscoveredURL(
        url="https://example.com/womens/tops",
        store_name="S",
        nav_text="Tops",
        discovery_method="sitemap",
    )
    checker = AsyncMock()
    checker.filter_allowed.return_value = [u1.url]
    extractor = TagExtractor()
    normalizer = TagNormalizer()
    result = await process([u1], checker, extractor, normalizer)
    assert len(result) >= 1
    checker.filter_allowed.assert_called_once()
    assert result[0].url == u1.url
    assert result[0].tags


@pytest.mark.asyncio
async def test_process_robots_blocks_some() -> None:
    allowed_url = "https://example.com/womens/tops"
    blocked_url = "https://example.com/blocked"
    u1 = DiscoveredURL(url=allowed_url, store_name="S", nav_text="Tops")
    u2 = DiscoveredURL(url=blocked_url, store_name="S")
    checker = AsyncMock()
    checker.filter_allowed.return_value = [allowed_url]
    extractor = TagExtractor()
    normalizer = TagNormalizer()
    result = await process([u1, u2], checker, extractor, normalizer)
    # Only u1 should be in result (u2 blocked by robots)
    urls = [r.url for r in result]
    assert allowed_url in urls
    assert blocked_url not in urls
