import asyncio
from typing import List
from bs4 import BeautifulSoup
from playwright.async_api import Page
from .product import Product
from ..utils.logger import get_logger

logger = get_logger(__name__)

class BaseScraper:
    def __init__(self, store_name: str):
        self.store_name = store_name
        self.base_url = ""

    async def scrape(self, page: Page, url: str, tags: list[str], dump_html: bool = False) -> List[Product]:
        """
        Navigates to the URL, waits for products to load, 
        and parses the HTML into Product objects.
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
        """must be implemented by subclasses"""
        raise NotImplementedError
