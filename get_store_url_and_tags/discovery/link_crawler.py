import asyncio
from collections import deque
from typing import List, Optional, Set, Dict
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page, Browser, async_playwright

from .base import DiscoveryStrategy, DiscoveredURL, StoreDefinition
from ..filters.url_classifier import URLClassifier
from ..filters.robots_checker import RobotsChecker
from ..utils.logger import get_logger
from ..utils.rate_limiter import RateLimiter

logger = get_logger(__name__)


class LinkCrawlerDiscovery(DiscoveryStrategy):
    """
    Discovers category URLs by crawling internal links using BFS up to a depth limit.
    
    This is the most thorough but slowest discovery method.
    """
    
    name = "link_crawler"
    
    def __init__(
        self,
        max_depth: int = 2,
        max_pages: int = 50,
        headless: bool = True,
        timeout: float = 30000,
        rate_limiter: RateLimiter = None,
        robots_checker: RobotsChecker = None,
        classifier: URLClassifier = None
    ):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.headless = headless
        self.timeout = timeout
        self.rate_limiter = rate_limiter or RateLimiter()
        self.robots_checker = robots_checker or RobotsChecker()
        self.classifier = classifier or URLClassifier()
        self._browser: Optional[Browser] = None
        self._playwright = None
    
    async def _get_browser(self) -> Browser:
        if self._browser is None or not self._browser.is_connected():
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
        return self._browser
    
    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def _create_page(self) -> Page:
        """Create a new page with stealth settings."""
        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)
        
        return page
    
    def _is_same_domain(self, url: str, domain: str) -> bool:
        """Check if URL belongs to the same domain."""
        try:
            parsed = urlparse(url)
            return domain in parsed.netloc
        except Exception:
            return False
    
    async def _extract_links(self, page: Page, store: StoreDefinition) -> List[Dict]:
        """Extract all links from the page."""
        links = []
        
        try:
            elements = await page.query_selector_all("a[href]")
            
            for element in elements:
                try:
                    href = await element.get_attribute("href")
                    text = await element.inner_text()
                    
                    if not href:
                        continue
                    
                    if href.startswith("/"):
                        parsed = urlparse(store.homepage)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                    elif href.startswith("#"):
                        continue
                    
                    if not self._is_same_domain(href, store.domain):
                        continue
                    
                    links.append({
                        "url": href.split("#")[0],
                        "text": text.strip() if text else None
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"[{store.name}] Failed to extract links: {e}")
        
        return links
    
    async def _get_page_metadata(self, page: Page) -> Dict:
        """Extract page title and breadcrumb text."""
        metadata = {"title": None, "breadcrumbs": None}
        
        try:
            metadata["title"] = await page.title()
        except Exception:
            pass
        
        breadcrumb_selectors = [
            "[aria-label='breadcrumb']",
            ".breadcrumb",
            ".breadcrumbs",
            "#breadcrumb",
            "[data-testid='breadcrumb']",
        ]
        
        for selector in breadcrumb_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    metadata["breadcrumbs"] = " > ".join(
                        part.strip() for part in text.split("\n") if part.strip()
                    )
                    break
            except Exception:
                continue
        
        return metadata
    
    async def discover(
        self,
        store: StoreDefinition,
        **kwargs
    ) -> List[DiscoveredURL]:
        """
        Discover category URLs by crawling links BFS-style.
        
        Args:
            store: Store definition
            
        Returns:
            List of discovered category URLs
        """
        logger.info(f"[{store.name}] Starting link crawler discovery (max_depth={self.max_depth})")
        
        page = await self._create_page()
        
        visited: Set[str] = set()
        queue: deque = deque()
        discovered: List[DiscoveredURL] = []
        
        queue.append((store.homepage, 0, None))
        visited.add(store.homepage.rstrip("/"))
        
        classifier = URLClassifier(
            extra_category_patterns=store.extra_category_patterns,
            extra_exclude_patterns=store.extra_exclude_patterns,
            max_path_depth=store.max_path_depth
        )
        
        pages_crawled = 0
        
        try:
            while queue and pages_crawled < self.max_pages:
                url, depth, nav_text = queue.popleft()
                
                if not await self.robots_checker.is_allowed(url):
                    continue
                
                await self.rate_limiter.acquire(store.domain)
                
                try:
                    logger.debug(f"[{store.name}] Crawling (depth={depth}): {url}")
                    
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=self.timeout
                    )
                    
                    await asyncio.sleep(2)
                    
                    pages_crawled += 1
                    
                    metadata = await self._get_page_metadata(page)
                    
                    if classifier.is_category_url(url, store.homepage):
                        discovered.append(DiscoveredURL(
                            url=url,
                            store_name=store.name,
                            nav_text=nav_text,
                            page_title=metadata["title"],
                            breadcrumb_text=metadata["breadcrumbs"],
                            discovery_method="link_crawler",
                            depth=depth
                        ))
                    
                    if depth < self.max_depth:
                        links = await self._extract_links(page, store)
                        
                        for link in links:
                            normalized = link["url"].rstrip("/")
                            if normalized not in visited:
                                visited.add(normalized)
                                queue.append((link["url"], depth + 1, link["text"]))
                    
                except Exception as e:
                    logger.warning(f"[{store.name}] Failed to crawl {url}: {e}")
                    continue
            
            logger.info(
                f"[{store.name}] Link crawler crawled {pages_crawled} pages, "
                f"found {len(discovered)} category URLs"
            )
            return discovered
            
        finally:
            await page.context.close()
