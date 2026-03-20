"""Tests for scraping.scrapers.american_eagle."""

from bs4 import BeautifulSoup

import pytest

from get_store_url_and_tags.scraping.scrapers.american_eagle import AmericanEagleScraper


def test_american_eagle_parse_html_data_qa() -> None:
    html = """
    <div data-qa="product-card">
      <h3>AE Shirt</h3>
      <div data-qa="price">$24.99</div>
      <a href="/p/shirt-1">Link</a>
      <img src="https://www.ae.com/img/1.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AmericanEagleScraper()
    products = scraper.parse_html(soup, ["Mens", "T-Shirts"])
    assert len(products) == 1
    assert products[0].item_name == "AE Shirt"
    assert products[0].price == "$24.99"
    assert products[0].item_link == "https://www.ae.com/p/shirt-1"
    assert products[0].tags == ["Mens", "T-Shirts"]


def test_american_eagle_parse_html_relative_link() -> None:
    html = """
    <div data-qa="product-card">
      <h3>Item</h3>
      <div data-qa="price">$10</div>
      <a href="/p/rel">L</a>
      <img src="/img/1.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AmericanEagleScraper()
    products = scraper.parse_html(soup, [])
    assert products[0].item_link == "https://www.ae.com/p/rel"


def test_american_eagle_parse_html_protocol_relative_image() -> None:
    html = """
    <div data-qa="product-card">
      <h3>Item</h3>
      <div data-qa="price">$10</div>
      <a href="/p/1">L</a>
      <img src="//www.ae.com/img/1.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AmericanEagleScraper()
    products = scraper.parse_html(soup, [])
    assert products[0].item_image_links == ["https://www.ae.com/img/1.jpg"]


def test_american_eagle_parse_html_name_none_skipped() -> None:
    html = """
    <div data-qa="product-card">
      <div data-qa="price">$10</div>
      <a href="/p/1">L</a>
      <img src="/i/1.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AmericanEagleScraper()
    products = scraper.parse_html(soup, [])
    # When name is 'None' (string), the code still appends if name != "None". So with no h3/h2/name div we get name = 'None' and product is still appended (the code says "if name != 'None':" then append). Let me check.
    # if name != "None": products.append(...). So when name is 'None' we don't append. So we need a card that has no name - then name_elem is None, name = 'None'... wait, name = name_elem.text.strip() if name_elem else 'None'. So name is 'None'. Then "if name != 'None'" is False so we don't append. So 0 products.
    assert len(products) == 0


def test_american_eagle_parse_html_multiple_images() -> None:
    html = """
    <div data-qa="product-card">
      <h3>Multi</h3>
      <div data-qa="price">$10</div>
      <a href="/p/1">L</a>
      <img src="https://www.ae.com/img/first.jpg" />
      <img src="//www.ae.com/img/second.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AmericanEagleScraper()
    products = scraper.parse_html(soup, [])
    assert products[0].item_image_links == [
        "https://www.ae.com/img/first.jpg",
        "https://www.ae.com/img/second.jpg",
    ]


def test_american_eagle_parse_html_dedupes_duplicate_image_urls() -> None:
    html = """
    <div data-qa="product-card">
      <h3>Dedupe</h3>
      <div data-qa="price">$10</div>
      <a href="/p/1">L</a>
      <img src="https://www.ae.com/img/x.jpg" />
      <img src="https://www.ae.com/img/x.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AmericanEagleScraper()
    products = scraper.parse_html(soup, [])
    assert products[0].item_image_links == ["https://www.ae.com/img/x.jpg"]


def test_american_eagle_parse_html_fallback_product_tile() -> None:
    html = """
    <div class="product-tile">
      <h2>Tile Item</h2>
      <span class="price">$15</span>
      <a href="/p/tile">L</a>
      <img src="/t.jpg" />
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AmericanEagleScraper()
    products = scraper.parse_html(soup, [])
    assert len(products) == 1
    assert "Tile" in products[0].item_name
