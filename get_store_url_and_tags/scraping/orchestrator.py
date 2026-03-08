import asyncio
from collections import defaultdict
from typing import List, Optional, TYPE_CHECKING
from playwright.async_api import async_playwright
from .scrapers import get_scraper_for_store
from .product import Product
from ..discovery.stores_links import StoreLink
from ..utils.logger import get_logger

if TYPE_CHECKING:
    from ..config import Settings

logger = get_logger(__name__)

# Max concurrent store tasks (browser contexts) to limit memory/CPU
MAX_CONCURRENT_STORES = 5


class ScrapingOrchestrator:
    """
    Orchestrates product scraping from a list of store configuration entries.
    Runs one task per store in parallel (each store uses one browser context, sequential within store).
    """
    def __init__(
        self,
        headless: bool = False,
        dump_item_html: bool = False,
        settings: Optional["Settings"] = None,
        max_concurrent_stores: int = MAX_CONCURRENT_STORES,
    ):
        self.headless = headless
        self.dump_item_html = dump_item_html
        self.settings = settings
        self.max_concurrent_stores = max_concurrent_stores

    async def _scrape_one_store(
        self,
        browser,
        store_name: str,
        store_entries: List[StoreLink],
        semaphore: asyncio.Semaphore,
    ) -> List[Product]:
        """Scrape all entries for a single store (one context, sequential requests)."""
        async with semaphore:
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
            products: List[Product] = []
            try:
                scraper = get_scraper_for_store(store_name)
                if not scraper:
                    logger.warning("No scraper available for store: %s, skipping %d URLs", store_name, len(store_entries))
                    return products
                page_wait = getattr(self.settings, "scrape_page_wait_seconds", 2.5) if self.settings else 2.5
                scroll_delay = getattr(self.settings, "scrape_scroll_delay_seconds", 0.6) if self.settings else 0.6
                scroll_count = getattr(self.settings, "scrape_scroll_count", 2) if self.settings else 2
                for entry in store_entries:
                    logger.info("Scraping products for %s at %s", store_name, entry.url)
                    batch = await scraper.scrape(
                        page,
                        entry.url,
                        entry.tags,
                        dump_html=self.dump_item_html,
                        page_wait_seconds=page_wait,
                        scroll_delay_seconds=scroll_delay,
                        scroll_count=scroll_count,
                    )
                    logger.info("Found %d products at %s", len(batch), entry.url)
                    products.extend(batch)
            finally:
                await context.close()
            return products

    async def run(
        self,
        entries: List[StoreLink],
        max_urls_per_shop: Optional[int] = None,
        sequential: bool = False,
    ) -> List[Product]:
        """
        Scrape products for the given store entries. Entries are grouped by store.
        By default each store is scraped in parallel (one context per store, sequential within store).
        If sequential=True, stores are scraped one at a time.
        """
        if max_urls_per_shop is not None:
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

        # Group by store name (preserve first-seen order)
        by_store: dict[str, List[StoreLink]] = defaultdict(list)
        for e in entries:
            by_store[e.name].append(e)
        per_store: List[tuple[str, List[StoreLink]]] = list(by_store.items())
        total_entries = len(entries)
        semaphore = asyncio.Semaphore(1 if sequential else self.max_concurrent_stores)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                if sequential:
                    all_products = []
                    for store_name, store_entries in per_store:
                        result = await self._scrape_one_store(
                            browser, store_name, store_entries, semaphore
                        )
                        all_products.extend(result)
                else:
                    results = await asyncio.gather(
                        *[
                            self._scrape_one_store(browser, store_name, store_entries, semaphore)
                            for store_name, store_entries in per_store
                        ],
                        return_exceptions=True,
                    )
                    all_products = []
                    for (store_name, _), result in zip(per_store, results):
                        if isinstance(result, Exception):
                            logger.error(
                                "[%s] Scraping failed: %s", store_name, result, exc_info=True
                            )
                        else:
                            all_products.extend(result)
            finally:
                await browser.close()

        logger.info("Scraping complete: %d products from %d entries", len(all_products), total_entries)
        return all_products
