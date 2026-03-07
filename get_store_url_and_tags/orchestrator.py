import asyncio
from typing import List, Optional, Dict

from .config import Config, load_config, Settings
from .discovery.base import DiscoveredURL, StoreDefinition
from .discovery.sitemap import SitemapDiscovery
from .discovery.navigation import NavigationDiscovery
from .discovery.link_crawler import LinkCrawlerDiscovery
from .filters.robots_checker import RobotsChecker
from .filters.url_classifier import URLClassifier
from .tagging.rules import TagExtractor
from .tagging.normalizer import TagNormalizer
from .discovery.stores_links import StoreLink
from .utils.logger import get_logger, setup_logging
from .utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class DiscoveryOrchestrator:
    """
    Orchestrates the URL discovery and tagging pipeline.
    
    Coordinates discovery strategies, filtering, tagging, and output.
    """
    
    def __init__(
        self,
        config: Config = None,
        headless: bool = True
    ):
        self.config = config or load_config()
        self.headless = headless
        
        self.rate_limiter = RateLimiter(
            default_delay=self.config.settings.rate_limit_seconds
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
            timeout=self.config.settings.request_timeout_seconds * 1000
        )
        self._link_discovery = LinkCrawlerDiscovery(
            max_depth=self.config.settings.max_crawl_depth,
            headless=headless,
            timeout=self.config.settings.request_timeout_seconds * 1000,
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
        logger.info(f"[{store.name}] Starting discovery (strategy={store.discovery_strategy})")
        
        discovered = []
        
        if store.discovery_strategy in ("auto", "sitemap"):
            try:
                results = await self._sitemap_discovery.discover(store)
                discovered.extend(results)
                
                if results and store.discovery_strategy == "auto":
                    logger.info(f"[{store.name}] Sitemap found {len(results)} URLs, skipping other strategies")
                    return discovered
            except Exception as e:
                logger.error(f"[{store.name}] Sitemap discovery failed: {e}")
        
        if store.discovery_strategy in ("auto", "navigation"):
            try:
                results = await self._nav_discovery.discover(store)
                discovered.extend(results)
                
                if results and store.discovery_strategy == "auto":
                    logger.info(f"[{store.name}] Navigation found {len(results)} URLs, skipping link crawler")
                    return discovered
            except Exception as e:
                logger.error(f"[{store.name}] Navigation discovery failed: {e}")
        
        if store.discovery_strategy in ("auto", "links"):
            try:
                # #region agent log
                import json as _json, time as _time, os as _os
                _log_path = "/home/rob/Coding/all-on/.cursor/debug-4cc033.log"
                try:
                    _os.makedirs(_os.path.dirname(_log_path), exist_ok=True)
                    with open(_log_path, "a") as _f:
                        _f.write(_json.dumps({"sessionId": "4cc033", "hypothesisId": "D", "location": "orchestrator.py:link_crawler", "message": "link crawler triggered", "data": {"store": store.name, "discovered_so_far": len(discovered)}, "timestamp": int(_time.time() * 1000)}) + "\n")
                except Exception:
                    pass
                # #endregion
                results = await self._link_discovery.discover(store)
                discovered.extend(results)
            except Exception as e:
                logger.error(f"[{store.name}] Link crawler discovery failed: {e}")
        
        logger.info(f"[{store.name}] Discovery complete: {len(discovered)} total URLs")
        return discovered
    
    def _deduplicate_urls(
        self,
        urls: List[DiscoveredURL]
    ) -> List[DiscoveredURL]:
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
    
    def _tag_urls(
        self,
        urls: List[DiscoveredURL]
    ) -> List[StoreLink]:
        """Extract and normalize tags for discovered URLs."""
        entries = []
        
        for url in urls:
            raw_tags = self.tag_extractor.extract(
                url=url.url,
                nav_text=url.nav_text,
                page_title=url.page_title,
                breadcrumb_text=url.breadcrumb_text
            )
            
            normalized_tags = self.tag_normalizer.normalize(raw_tags)
            
            if normalized_tags:
                entries.append(StoreLink(
                    name=url.store_name,
                    url=url.url,
                    tags=normalized_tags
                ))
            else:
                logger.warning(f"No tags extracted for {url.url}, skipping")
        
        return entries
    
    async def run(
        self,
        stores: List[str] = None,
        dump_urls: bool = False
    ) -> List[StoreLink]:
        """
        Run the full discovery pipeline.
        
        Args:
            stores: List of store names to process (None = all)
            dump_urls: If True, write discovered URLs to debug folder
            
        Returns:
            List of discovered and tagged entries
        """
        setup_logging()
        
        stores_to_process = self.config.stores
        if stores:
            stores_to_process = [s for s in stores_to_process if s.name in stores]
        
        if not stores_to_process:
            logger.warning("No stores to process")
            return []
        
        logger.info(f"Starting discovery for {len(stores_to_process)} stores")
        
        all_discovered: List[DiscoveredURL] = []
        
        for store in stores_to_process:
            try:
                urls = await self._discover_store(store)
                all_discovered.extend(urls)
            except Exception as e:
                logger.error(f"[{store.name}] Discovery failed: {e}", exc_info=True)
        
        allowed_urls = set(await self.robots_checker.filter_allowed(
            [u.url for u in all_discovered]
        ))
        all_discovered = [u for u in all_discovered if u.url in allowed_urls]
        
        unique_urls = self._deduplicate_urls(all_discovered)
        logger.info(f"Deduplicated to {len(unique_urls)} unique URLs")
        
        entries = self._tag_urls(unique_urls)
        logger.info(f"Tagged {len(entries)} URLs")
        
        if dump_urls and entries:
            import json
            from pathlib import Path
            import time
            from dataclasses import asdict
            
            debug_dir = Path(__file__).parent / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            # Group by store
            by_store = {}
            for entry in entries:
                if entry.name not in by_store:
                    by_store[entry.name] = []
                by_store[entry.name].append(asdict(entry))
                
            for store_name, store_urls in by_store.items():
                timestamp = int(time.time())
                debug_file = debug_dir / f"{store_name.lower().replace(' ', '_')}_urls_{timestamp}.json"
                with open(debug_file, "w") as f:
                    json.dump(store_urls, f, indent=2)
                logger.info(f"Dumped {len(store_urls)} URLs for {store_name} to {debug_file}")
        
        return entries
    
    async def close(self):
        """Clean up resources."""
        await self._sitemap_discovery.close()
        await self._nav_discovery.close()
        await self._link_discovery.close()
