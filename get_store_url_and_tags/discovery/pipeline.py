"""
Post-processing pipeline: filter by robots.txt, deduplicate, then tag.

Turns raw DiscoveredURL list into List[StoreLink] for scraping.
"""

from typing import Dict, List

from ..models import DiscoveredURL, StoreLink
from ..filters.robots_checker import RobotsChecker
from ..tagging.rules import TagExtractor
from ..tagging.normalizer import TagNormalizer
from ..utils.logger import get_logger

logger = get_logger(__name__)


def deduplicate_urls(urls: List[DiscoveredURL]) -> List[DiscoveredURL]:
    """Remove duplicate URLs, keeping the one with most metadata."""
    seen: Dict[str, DiscoveredURL] = {}

    for url in urls:
        key = url.url.rstrip("/")

        if key not in seen:
            seen[key] = url
        else:
            existing = seen[key]
            if (url.nav_text and not existing.nav_text) or \
               (url.page_title and not existing.page_title) or \
               (url.breadcrumb_text and not existing.breadcrumb_text):
                merged = DiscoveredURL(
                    url=url.url,
                    store_name=url.store_name,
                    nav_text=url.nav_text or existing.nav_text,
                    page_title=url.page_title or existing.page_title,
                    breadcrumb_text=url.breadcrumb_text or existing.breadcrumb_text,
                    discovery_method=url.discovery_method,
                    depth=min(url.depth, existing.depth)
                )
                seen[key] = merged

    return list(seen.values())


def tag_urls(
    urls: List[DiscoveredURL],
    tag_extractor: TagExtractor,
    tag_normalizer: TagNormalizer,
) -> List[StoreLink]:
    """Extract and normalize tags for discovered URLs."""
    entries = []

    for url in urls:
        raw_tags = tag_extractor.extract(
            url=url.url,
            nav_text=url.nav_text,
            page_title=url.page_title,
            breadcrumb_text=url.breadcrumb_text
        )

        normalized_tags = tag_normalizer.normalize(raw_tags)

        if normalized_tags:
            entries.append(StoreLink(
                name=url.store_name,
                url=url.url,
                tags=normalized_tags
            ))
        else:
            logger.warning("No tags extracted for %s, skipping", url.url)

    return entries


async def process(
    discovered_urls: List[DiscoveredURL],
    robots_checker: RobotsChecker,
    tag_extractor: TagExtractor,
    tag_normalizer: TagNormalizer,
) -> List[StoreLink]:
    """
    Filter by robots.txt, deduplicate, then tag.
    Returns list of StoreLink ready for scraping.
    """
    if not discovered_urls:
        return []

    allowed_urls = set(await robots_checker.filter_allowed([u.url for u in discovered_urls]))
    filtered = [u for u in discovered_urls if u.url in allowed_urls]

    unique_urls = deduplicate_urls(filtered)
    logger.info("Deduplicated to %d unique URLs", len(unique_urls))

    entries = tag_urls(unique_urls, tag_extractor, tag_normalizer)
    logger.info("Tagged %d URLs", len(entries))

    return entries
