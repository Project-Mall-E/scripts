"""
Base scraper for product listing pages. Subclass and implement parse_html().
Use --dump-item-html to save page HTML to debug/ when writing a new parser.
"""
import asyncio
from typing import List
from bs4 import BeautifulSoup
from playwright.async_api import Page
from .product import Product
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BaseScraper:
    """Base class for per-store product listing parsers. Subclasses must implement parse_html()."""

    def __init__(self, store_name: str):
        self.store_name = store_name
        self.base_url = ""  # e.g. https://www.ae.com for resolving relative links

    def content_ready_selector(self) -> str | None:
        """Optional: CSS selector to wait for before capturing HTML. Override in subclasses if content is JS-rendered."""
        return None

    async def scrape(
        self,
        page: Page,
        url: str,
        tags: list[str],
        dump_html: bool = False,
        page_wait_seconds: float = 2.5,
        scroll_delay_seconds: float = 0.6,
        scroll_count: int = 2,
    ) -> List[Product]:
        """
        Navigate to the category URL, wait for content, then parse HTML into Product list.
        If dump_html is True, saves HTML to debug/<safe_url>-dump.html for parser development.
        """
        logger.info(f"[{self.store_name}] Navigating to {url} ...")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            logger.info(f"[{self.store_name}] Page loaded. Waiting for any bot checks to complete...")
            await asyncio.sleep(page_wait_seconds)
            # Wait for product grid if scraper defines a selector (e.g. JS-rendered catalog)
            ready_selector = self.content_ready_selector()
            if ready_selector:
                try:
                    logger.info(f"[{self.store_name}] Waiting for content selector: {ready_selector!r}")
                    await page.wait_for_selector(ready_selector, timeout=15000)
                except Exception as e:
                    logger.warning(f"[{self.store_name}] Timeout or error waiting for selector: {e}")
            # Add some scrolling to seem human
            for _ in range(scroll_count):
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(scroll_delay_seconds)
                
            logger.info(f"[{self.store_name}] Fetching page content ...")
            html = await page.content()
            logger.info(f"[{self.store_name}] Content received (%d bytes), parsing HTML ...", len(html))

            if dump_html:
                import urllib.parse
                from pathlib import Path
                debug_dir = Path("debug")
                debug_dir.mkdir(exist_ok=True)
                safe_url = urllib.parse.quote_plus(url)
                dump_path = debug_dir / f"{safe_url}-dump.html"
                dump_path.write_text(html, encoding="utf-8")
                logger.info(f"[{self.store_name}] Dumped HTML to {dump_path}")

            soup = BeautifulSoup(html, "html.parser")
            logger.info(f"[{self.store_name}] Calling parse_html ...")
            products = self.parse_html(soup, tags)
            logger.info(f"[{self.store_name}] parse_html returned %d products", len(products))
            return products
        except Exception as e:
            logger.error(f"[{self.store_name}] Failed to scrape {url}: {e}")
            return []

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        """
        Parse product listing HTML into Product objects. Implement in each store scraper.
        tags are the category tags (e.g. from breadcrumbs) to attach to each product.
        """
        raise NotImplementedError
