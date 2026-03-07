import asyncio
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import aiohttp

from .base import DiscoveryStrategy, DiscoveredURL, StoreDefinition
from ..filters.url_classifier import URLClassifier
from ..utils.logger import get_logger
from ..utils.retry import retry_with_backoff

logger = get_logger(__name__)

SITEMAP_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class SitemapDiscovery(DiscoveryStrategy):
    """
    Discovers category URLs by parsing sitemap.xml files.
    
    Handles both simple sitemaps and sitemap indexes.
    """
    
    name = "sitemap"
    
    def __init__(
        self,
        timeout: float = 30.0,
        max_sitemaps: int = 10,
        classifier: URLClassifier = None
    ):
        self.timeout = timeout
        self.max_sitemaps = max_sitemaps
        self.classifier = classifier or URLClassifier()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "ClothingAggregatorBot/1.0"}
            )
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    @retry_with_backoff(max_retries=2, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def _fetch_sitemap(self, url: str) -> Optional[str]:
        """Fetch sitemap content from URL."""
        session = await self._get_session()
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                logger.debug(f"Sitemap not found at {url} (status {response.status})")
                return None
        except Exception as e:
            logger.warning(f"Failed to fetch sitemap {url}: {e}")
            return None
    
    def _parse_sitemap_index(self, content: str) -> List[str]:
        """Parse sitemap index XML to get sitemap URLs."""
        try:
            root = ET.fromstring(content)
            urls = []
            
            for sitemap in root.findall(".//sm:sitemap/sm:loc", SITEMAP_NAMESPACE):
                if sitemap.text:
                    urls.append(sitemap.text.strip())
            
            if not urls:
                for sitemap in root.findall(".//sitemap/loc"):
                    if sitemap.text:
                        urls.append(sitemap.text.strip())
            
            return urls[:self.max_sitemaps]
        except ET.ParseError as e:
            logger.warning(f"Failed to parse sitemap index: {e}")
            return []
    
    def _parse_sitemap_urls(self, content: str) -> List[str]:
        """Parse sitemap XML to get page URLs."""
        try:
            root = ET.fromstring(content)
            urls = []
            
            for url_elem in root.findall(".//sm:url/sm:loc", SITEMAP_NAMESPACE):
                if url_elem.text:
                    urls.append(url_elem.text.strip())
            
            if not urls:
                for url_elem in root.findall(".//url/loc"):
                    if url_elem.text:
                        urls.append(url_elem.text.strip())
            
            return urls
        except ET.ParseError as e:
            logger.warning(f"Failed to parse sitemap: {e}")
            return []
    
    def _is_sitemap_index(self, content: str) -> bool:
        """Check if content is a sitemap index (contains other sitemaps)."""
        return "<sitemapindex" in content.lower()
    
    async def discover(
        self,
        store: StoreDefinition,
        **kwargs
    ) -> List[DiscoveredURL]:
        """
        Discover category URLs from store's sitemap.
        
        Args:
            store: Store definition
            
        Returns:
            List of discovered category URLs
        """
        logger.info(f"[{store.name}] Starting sitemap discovery")
        
        parsed = urlparse(store.homepage)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        sitemap_urls_to_try = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemaps/sitemap.xml",
        ]
        
        all_page_urls = []
        
        for sitemap_url in sitemap_urls_to_try:
            content = await self._fetch_sitemap(sitemap_url)
            if not content:
                continue
            
            logger.info(f"[{store.name}] Found sitemap at {sitemap_url}")
            
            if self._is_sitemap_index(content):
                child_sitemaps = self._parse_sitemap_index(content)
                logger.info(f"[{store.name}] Sitemap index contains {len(child_sitemaps)} sitemaps")
                
                for child_url in child_sitemaps:
                    child_content = await self._fetch_sitemap(child_url)
                    if child_content and not self._is_sitemap_index(child_content):
                        urls = self._parse_sitemap_urls(child_content)
                        all_page_urls.extend(urls)
            else:
                urls = self._parse_sitemap_urls(content)
                all_page_urls.extend(urls)
            
            break
        
        if not all_page_urls:
            logger.info(f"[{store.name}] No URLs found in sitemaps")
            return []
        
        logger.info(f"[{store.name}] Found {len(all_page_urls)} total URLs in sitemap")
        
        # #region agent log
        import json as _json, time as _time, os as _os
        _log_path = "/home/rob/Coding/all-on/.cursor/debug-4cc033.log"
        _parsed_hp = urlparse(store.homepage)
        _hp_prefix = _parsed_hp.path.rstrip("/")
        _locale_urls = [u for u in all_page_urls if (urlparse(u).path.startswith(_hp_prefix) if _hp_prefix else True)]
        _locale_match = len(_locale_urls)
        _depth_hist = {}
        for _u in _locale_urls[:2000]:
            _d = len([s for s in urlparse(_u).path.strip("/").split("/") if s])
            _depth_hist[str(_d)] = _depth_hist.get(str(_d), 0) + 1
        _sample_urls = all_page_urls[:20]
        try:
            _os.makedirs(_os.path.dirname(_log_path), exist_ok=True)
            with open(_log_path, "a") as _f:
                _f.write(_json.dumps({"sessionId": "4cc033", "hypothesisId": "E", "location": "sitemap.py:pre-filter", "message": "sitemap locale/depth snapshot", "data": {"store": store.name, "total": len(all_page_urls), "homepage": store.homepage, "path_prefix": _hp_prefix, "locale_matching_prefix": _locale_match, "depth_hist_sampled_first_2000": _depth_hist, "sample": _sample_urls}, "timestamp": int(_time.time() * 1000)}) + "\n")
        except Exception:
            pass
        # #endregion

        classifier = URLClassifier(
            extra_category_patterns=store.extra_category_patterns,
            extra_exclude_patterns=store.extra_exclude_patterns,
            max_path_depth=store.max_path_depth
        )
        category_urls = classifier.filter_category_urls(all_page_urls, store.homepage)

        # #region agent log
        _passing_samples = category_urls[:30]
        try:
            with open(_log_path, "a") as _f:
                _f.write(_json.dumps({"sessionId": "4cc033", "hypothesisId": "A_post", "location": "sitemap.py:post-filter", "message": "URLs passing classifier after locale+depth filter", "data": {"store": store.name, "count": len(category_urls), "sample_passing": _passing_samples}, "timestamp": int(_time.time() * 1000)}) + "\n")
        except Exception:
            pass
        # #endregion
        
        discovered = [
            DiscoveredURL(
                url=url,
                store_name=store.name,
                discovery_method="sitemap"
            )
            for url in category_urls
        ]
        
        logger.info(f"[{store.name}] Sitemap discovery found {len(discovered)} category URLs")
        return discovered
