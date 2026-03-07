"""Store configuration model."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StoreDefinition:
    """
    Configuration for a store to crawl (from config/stores.json).
    name must match a scraper STORE_NAME in scraping/scrapers/ to scrape products.
    """

    name: str  # display name; must match scraper STORE_NAME for product scraping
    homepage: str  # start URL for discovery
    domain: str  # e.g. ae.com; used for robots.txt
    discovery_strategy: str = "auto"  # auto | sitemap | navigation | links
    extra_category_patterns: List[str] = field(default_factory=list)  # regex; URLs matching are kept
    extra_exclude_patterns: List[str] = field(default_factory=list)  # regex; URLs matching are dropped
    max_path_depth: Optional[int] = None  # max path segments (e.g. 3 = /a/b/c)
