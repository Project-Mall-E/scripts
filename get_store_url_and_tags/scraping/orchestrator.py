import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright
from .scrapers import get_scraper_for_store
from .product import Product
from ..discovery.stores_links import StoreLink
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ScrapingOrchestrator:
    """
    Orchestrates product scraping from a list of store configuration entries.
    """
    def __init__(self, headless: bool = False, dump_item_html: bool = False):
        self.headless = headless
        self.dump_item_html = dump_item_html

    async def run(self, entries: List[StoreLink], max_urls_per_shop: Optional[int] = None) -> List[Product]:
        """
        Scrape products for the given store entries.
        """
        if max_urls_per_shop is not None:
            from collections import defaultdict
            shop_counts: dict[str, int] = defaultdict(int)
            filtered_entries = []
            for e in entries:
                if shop_counts[e.name] < max_urls_per_shop:
                    filtered_entries.append(e)
                    shop_counts[e.name] += 1
            entries = filtered_entries

        if not entries:
            logger.warning("No entries to scrape")
            return []

        all_products = []
        total_entries = len(entries)

        async with async_playwright() as p:
            # NOTE: headless=False typically required for bot protection (like Akamai)
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
            )
            page = await context.new_page()
            
            # Inject stealth properties to avoid WebDriver detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """)

            for i, entry in enumerate(entries):
                percentage = (i / total_entries) * 100
                print(f"\r[Scraping Progress] {percentage:.1f}% ({i}/{total_entries}) - {entry.name}", end="", flush=True)

                scraper = get_scraper_for_store(entry.name)
                if not scraper:
                    logger.warning(f"\nNo scraper available for store: {entry.name}, skipping {entry.url}")
                    continue
                
                logger.info(f"\nScraping products for {entry.name} at {entry.url}")
                products = await scraper.scrape(page, entry.url, entry.tags, dump_html=self.dump_item_html)
                logger.info(f"Found {len(products)} products at {entry.url}")
                all_products.extend(products)

            print(f"\r[Scraping Progress] 100.0% ({total_entries}/{total_entries}) - Done!{' ' * 20}")
            await browser.close()

        return all_products
