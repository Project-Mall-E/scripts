"""Tests for scraping.scrapers registry."""

import pytest

from get_store_url_and_tags.scraping.scrapers import (
    get_registered_store_names,
    get_scraper_for_store,
)
from get_store_url_and_tags.scraping.scrapers.abercrombie import (
    STORE_NAME as ABERCROMBIE_NAME,
    AbercrombieScraper,
)
from get_store_url_and_tags.scraping.scrapers.american_eagle import (
    STORE_NAME as AMERICAN_EAGLE_NAME,
    AmericanEagleScraper,
)


def test_get_scraper_for_store_abercrombie() -> None:
    scraper = get_scraper_for_store(ABERCROMBIE_NAME)
    assert scraper is not None
    assert isinstance(scraper, AbercrombieScraper)
    assert scraper.store_name == ABERCROMBIE_NAME


def test_get_scraper_for_store_american_eagle() -> None:
    scraper = get_scraper_for_store(AMERICAN_EAGLE_NAME)
    assert scraper is not None
    assert isinstance(scraper, AmericanEagleScraper)
    assert scraper.store_name == AMERICAN_EAGLE_NAME


def test_get_scraper_for_store_unknown() -> None:
    assert get_scraper_for_store("UnknownStore") is None


def test_get_registered_store_names() -> None:
    names = get_registered_store_names()
    assert ABERCROMBIE_NAME in names
    assert AMERICAN_EAGLE_NAME in names
    assert isinstance(names, list)
