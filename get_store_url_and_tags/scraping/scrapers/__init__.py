"""
Per-store product parsers (scrapers). Each store has its own module;
this package registers them and exposes get_scraper_for_store().

How to add a new parser (see README §3):
  1. Dump sample HTML: run with --dump-item-html --max-urls-per-shop 1 --stores StoreName.
  2. Create scrapers/<store_slug>.py with STORE_NAME (must match config stores.json "name")
     and a BaseScraper subclass implementing parse_html(soup, tags) -> List[Product].
  3. Import the module and add STORE_NAME -> ScraperClass to _REGISTRY below.
"""

from typing import Optional

from ..base import BaseScraper

# Import each store scraper and register by STORE_NAME
from . import abercrombie
from . import american_eagle

_REGISTRY: dict[str, type[BaseScraper]] = {
    abercrombie.STORE_NAME: abercrombie.AbercrombieScraper,
    american_eagle.STORE_NAME: american_eagle.AmericanEagleScraper,
}


def get_scraper_for_store(store_name: str) -> Optional[BaseScraper]:
    """Return a scraper instance for the given store name, or None if none is implemented."""
    scraper_class = _REGISTRY.get(store_name)
    if scraper_class is None:
        return None
    return scraper_class()


def get_registered_store_names() -> list[str]:
    """Return list of store names that have a scraper (for debugging or docs)."""
    return list(_REGISTRY.keys())
