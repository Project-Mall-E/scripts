"""Discovery orchestrator: runs strategies and returns tagged StoreLinks via pipeline."""

import asyncio
from typing import List, Optional

from .config import Config, load_config
from .models import DiscoveredURL, StoreDefinition, StoreLink
from .discovery.sitemap import SitemapDiscovery
from .discovery.navigation import NavigationDiscovery
from .discovery.link_crawler import LinkCrawlerDiscovery
from .discovery.pipeline import process as pipeline_process
from .filters.robots_checker import RobotsChecker
from .tagging.rules import TagExtractor
from .tagging.normalizer import TagNormalizer
from .utils.logger import get_logger, setup_logging
from .utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class DiscoveryOrchestrator:
    """
    Orchestrates URL discovery: runs strategies per store, then pipeline (filter, dedupe, tag).
    Returns List[StoreLink]. Dump/output is handled by the app layer.
    """

    def __init__(
        self,
        config: Config = None,
        headless: bool = True
    ):
        self.config = config or load_config()
        self.headless = headless

        self.rate_limiter = RateLimiter(
            default_delay=self.config.settings.rate_limit_seconds,
            jitter_seconds=self.config.settings.rate_limit_jitter,
        )
        self.robots_checker = RobotsChecker(
            timeout=self.config.settings.request_timeout_seconds
        )
        self.tag_extractor = TagExtractor()
        self.tag_normalizer = TagNormalizer()

        self._sitemap_discovery = SitemapDiscovery(
            timeout=self.config.settings.request_timeout_seconds
        )
        self._nav_discovery = NavigationDiscovery(
            headless=headless,
            timeout=self.config.settings.request_timeout_seconds * 1000,
            wait_for_nav=self.config.settings.navigation_wait_seconds,
            hover_delay_seconds=self.config.settings.navigation_hover_delay_seconds,
            post_hover_seconds=self.config.settings.navigation_post_hover_seconds,
        )
        self._link_discovery = LinkCrawlerDiscovery(
            max_depth=self.config.settings.max_crawl_depth,
            headless=headless,
            timeout=self.config.settings.request_timeout_seconds * 1000,
            post_goto_seconds=self.config.settings.link_crawler_post_goto_seconds,
            rate_limiter=self.rate_limiter,
            robots_checker=self.robots_checker
        )

    async def _discover_store(
        self,
        store: StoreDefinition
    ) -> List[DiscoveredURL]:
        """
        Run discovery strategies for a single store.

        Tries strategies in order based on store.discovery_strategy:
        - "auto": sitemap -> navigation -> link_crawler (stops when results found)
        - "sitemap": sitemap only
        - "navigation": navigation only
        - "links": link_crawler only
        """
        logger.info("[%s] Starting discovery (strategy=%s)", store.name, store.discovery_strategy)

        discovered = []

        if store.discovery_strategy in ("auto", "sitemap"):
            try:
                results = await self._sitemap_discovery.discover(store)
                discovered.extend(results)

                if results and store.discovery_strategy == "auto":
                    logger.info("[%s] Sitemap found %d URLs, skipping other strategies", store.name, len(results))
                    return discovered
            except Exception as e:
                logger.error("[%s] Sitemap discovery failed: %s", store.name, e)

        if store.discovery_strategy in ("auto", "navigation"):
            try:
                results = await self._nav_discovery.discover(store)
                discovered.extend(results)

                if results and store.discovery_strategy == "auto":
                    logger.info("[%s] Navigation found %d URLs, skipping link crawler", store.name, len(results))
                    return discovered
            except Exception as e:
                logger.error("[%s] Navigation discovery failed: %s", store.name, e)

        if store.discovery_strategy in ("auto", "links"):
            try:
                results = await self._link_discovery.discover(store)
                discovered.extend(results)
            except Exception as e:
                logger.error("[%s] Link crawler discovery failed: %s", store.name, e)

        logger.info("[%s] Discovery complete: %d total URLs", store.name, len(discovered))
        return discovered

    async def run(
        self,
        stores: Optional[List[str]] = None,
        sequential: bool = False,
    ) -> List[StoreLink]:
        """
        Run discovery for configured stores, then filter/dedupe/tag via pipeline.

        Args:
            stores: List of store names to process (None = all)
            sequential: If True, run one store at a time; otherwise run stores in parallel

        Returns:
            List of discovered and tagged StoreLinks (no dump; caller handles output).
        """
        setup_logging()

        stores_to_process = self.config.stores
        if stores:
            stores_to_process = [s for s in stores_to_process if s.name in stores]

        if not stores_to_process:
            logger.warning("No stores to process")
            return []

        logger.info(
            "Starting discovery for %d stores (%s)",
            len(stores_to_process),
            "sequential" if sequential else "parallel",
        )

        all_discovered: List[DiscoveredURL] = []
        if sequential:
            for store in stores_to_process:
                try:
                    urls = await self._discover_store(store)
                    all_discovered.extend(urls)
                except Exception as e:
                    logger.error("[%s] Discovery failed: %s", store.name, e, exc_info=True)
        else:
            results = await asyncio.gather(
                *[self._discover_store(store) for store in stores_to_process],
                return_exceptions=True,
            )
            for store, result in zip(stores_to_process, results):
                if isinstance(result, Exception):
                    logger.error("[%s] Discovery failed: %s", store.name, result, exc_info=True)
                else:
                    all_discovered.extend(result)

        entries = await pipeline_process(
            all_discovered,
            self.robots_checker,
            self.tag_extractor,
            self.tag_normalizer,
        )

        return entries

    async def close(self) -> None:
        """Clean up resources."""
        await self._sitemap_discovery.close()
        await self._nav_discovery.close()
        await self._link_discovery.close()
