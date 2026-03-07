import asyncio
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page, Browser, async_playwright

from .base import DiscoveryStrategy, DiscoveredURL, StoreDefinition
from ..filters.url_classifier import URLClassifier
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NavigationDiscovery(DiscoveryStrategy):
    """
    Discovers category URLs by crawling navigation menus using Playwright.
    
    Handles JavaScript-rendered navigation and extracts link text for tagging.
    """
    
    name = "navigation"
    
    NAV_SELECTORS = [
        "nav a",
        "header a",
        "[role='navigation'] a",
        ".nav a",
        ".navigation a",
        ".menu a",
        ".main-nav a",
        ".primary-nav a",
        ".site-nav a",
        "#nav a",
        "#navigation a",
        "#menu a",
        "[data-nav] a",
        "[data-menu] a",
    ]
    
    def __init__(
        self,
        headless: bool = True,
        timeout: float = 30000,
        wait_for_nav: float = 3.0,
        classifier: URLClassifier = None
    ):
        self.headless = headless
        self.timeout = timeout
        self.wait_for_nav = wait_for_nav
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
    
    async def _extract_nav_links(self, page: Page, store: StoreDefinition) -> List[dict]:
        """Extract links from navigation elements."""
        links = []
        
        combined_selector = ", ".join(self.NAV_SELECTORS)
        
        try:
            elements = await page.query_selector_all(combined_selector)
            
            for element in elements:
                try:
                    href = await element.get_attribute("href")
                    text = await element.inner_text()
                    
                    if href:
                        if href.startswith("/"):
                            parsed = urlparse(store.homepage)
                            href = f"{parsed.scheme}://{parsed.netloc}{href}"
                        
                        links.append({
                            "url": href,
                            "text": text.strip() if text else None
                        })
                except Exception:
                    continue
            
        except Exception as e:
            logger.warning(f"[{store.name}] Failed to extract nav links: {e}")
        
        return links
    
    async def _hover_nav_menus(self, page: Page) -> None:
        """Hover over main nav items to reveal dropdowns."""
        hover_selectors = [
            "nav > ul > li",
            "header nav li",
            ".nav > li",
            ".main-nav > li",
            "[role='navigation'] > ul > li",
        ]
        
        for selector in hover_selectors:
            try:
                items = await page.query_selector_all(selector)
                for item in items[:10]:
                    try:
                        await item.hover()
                        await asyncio.sleep(0.3)
                    except Exception:
                        continue
            except Exception:
                continue
    
    async def _get_page_title(self, page: Page) -> Optional[str]:
        """Get the page title."""
        try:
            return await page.title()
        except Exception:
            return None
    
    async def discover(
        self,
        store: StoreDefinition,
        **kwargs
    ) -> List[DiscoveredURL]:
        """
        Discover category URLs from navigation menus.
        
        Args:
            store: Store definition
            
        Returns:
            List of discovered category URLs with nav text
        """
        logger.info(f"[{store.name}] Starting navigation discovery")
        
        page = await self._create_page()
        
        try:
            await page.goto(
                store.homepage,
                wait_until="domcontentloaded",
                timeout=self.timeout
            )
            
            await asyncio.sleep(self.wait_for_nav)
            
            await self._hover_nav_menus(page)
            await asyncio.sleep(1)
            
            links = await self._extract_nav_links(page, store)
            logger.info(f"[{store.name}] Extracted {len(links)} navigation links")
            
            classifier = URLClassifier(
                extra_category_patterns=store.extra_category_patterns,
                extra_exclude_patterns=store.extra_exclude_patterns,
                max_path_depth=store.max_path_depth
            )
            
            discovered = []
            seen_urls = set()
            
            for link in links:
                url = link["url"].rstrip("/").split("#")[0]
                
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                if classifier.is_category_url(url, store.homepage):
                    discovered.append(DiscoveredURL(
                        url=link["url"],
                        store_name=store.name,
                        nav_text=link["text"],
                        discovery_method="navigation"
                    ))
            
            logger.info(f"[{store.name}] Navigation discovery found {len(discovered)} category URLs")
            return discovered
            
        except Exception as e:
            logger.error(f"[{store.name}] Navigation discovery failed: {e}")
            return []
        finally:
            await page.context.close()
