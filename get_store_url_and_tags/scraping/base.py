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

    async def scrape(self, page: Page, url: str, tags: list[str], dump_html: bool = False) -> List[Product]:
        """
        Navigate to the category URL, wait for content, then parse HTML into Product list.
        If dump_html is True, saves HTML to debug/<safe_url>-dump.html for parser development.
        """
        logger.info(f"[{self.store_name}] Navigating to {url} ...")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            logger.info(f"[{self.store_name}] Page loaded. Waiting for any bot checks to complete...")
            await asyncio.sleep(5)
            # Add some scrolling to seem human
            for _ in range(3):
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(1)
                
            html = await page.content()
            
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
            return self.parse_html(soup, tags)
        except Exception as e:
            logger.error(f"[{self.store_name}] Failed to scrape {url}: {e}")
            return []

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        """
        Parse product listing HTML into Product objects. Implement in each store scraper.
        tags are the category tags (e.g. from breadcrumbs) to attach to each product.
        """
        raise NotImplementedError
