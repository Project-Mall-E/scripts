"""Tests for scraping.scrapers.abercrombie."""

from bs4 import BeautifulSoup

from get_store_url_and_tags.scraping.scrapers.abercrombie import (
    AbercrombieScraper,
    _class_contains,
    _product_name_only,
)


def test_class_contains_list() -> None:
    assert _class_contains(["productCard-module__productCard"], "productCard") is True
    assert _class_contains(["other"], "productCard") is False
    assert _class_contains([], "x") is False


def test_class_contains_str() -> None:
    assert _class_contains("link-button", "link") is True
    assert _class_contains("link-button", "link", case_sensitive=False) is True


def test_class_contains_case_insensitive() -> None:
    assert _class_contains("LINK", "link", case_sensitive=False) is True


def test_product_name_only_empty() -> None:
    assert _product_name_only("") == ""
    assert _product_name_only(None) == ""


def test_product_name_only_activating_element() -> None:
    assert _product_name_only("Activating this element") == ""


def test_product_name_only_strips_price() -> None:
    assert _product_name_only("Cool Shirt $14.95") == "Cool Shirt"
    assert _product_name_only("Item Price After 25% Off") == "Item"


def test_product_name_only_first_line() -> None:
    assert _product_name_only("Line1\nLine2") == "Line1"


def test_abercrombie_content_ready_selector() -> None:
    s = AbercrombieScraper()
    sel = s.content_ready_selector()
    assert sel is not None
    assert "catalog-product-card" in sel


def test_abercrombie_parse_html_data_testid() -> None:
    html = """
    <div>
      <li data-testid="catalog-product-card">
        <span data-testid="catalog-product-card-name">Shirt Name</span>
        <span data-testid="product-price">$29.00</span>
        <a href="/p/shirt-1">Link</a>
        <img src="/img/shirt.jpg" />
      </li>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, ["Womens", "Tops"])
    assert len(products) == 1
    assert products[0].item_name == "Shirt Name"
    assert products[0].price == "$29.00"
    assert products[0].item_link == "https://www.abercrombie.com/p/shirt-1"
    assert products[0].tags == ["Womens", "Tops"]


def test_abercrombie_parse_html_fallback_class() -> None:
    html = """
    <li class="productCard-module__productCard">
      <h2>Fallback Shirt</h2>
      <span class="price-value">$19</span>
      <a href="/p/2">L</a>
      <img src="/i/2.jpg" />
    </li>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, [])
    assert len(products) == 1
    assert "Fallback" in products[0].item_name
    assert products[0].price == "$19"


def test_abercrombie_parse_html_relative_link() -> None:
    html = """
    <li data-testid="catalog-product-card">
      <span data-testid="catalog-product-card-name">X</span>
      <span data-testid="product-price">$1</span>
      <a href="/p/rel">L</a>
      <img src="/i/1.jpg" />
    </li>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, [])
    assert products[0].item_link == "https://www.abercrombie.com/p/rel"


def test_abercrombie_parse_html_duplicate_dollar_cleanup() -> None:
    html = """
    <li data-testid="catalog-product-card">
      <span data-testid="catalog-product-card-name">Y</span>
      <span data-testid="product-price">$25$25</span>
      <a href="/p/3">L</a>
      <img src="/i/3.jpg" />
    </li>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, [])
    assert products[0].price == "$25"


def test_abercrombie_parse_html_rejects_1x1_gif_data_uri_image() -> None:
    html = """
    <div>
      <li data-testid="catalog-product-card">
        <span data-testid="catalog-product-card-name">Shirt Name</span>
        <span data-testid="product-price">$29.00</span>
        <a href="/p/shirt-1">Link</a>
        <img src="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw" />
      </li>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, ["Womens", "Tops"])
    assert len(products) == 1
    assert products[0].item_image_link == "None"


def test_abercrombie_parse_html_resolves_relative_image() -> None:
    html = """
    <div>
      <li data-testid="catalog-product-card">
        <span data-testid="catalog-product-card-name">Shirt Name</span>
        <span data-testid="product-price">$29.00</span>
        <a href="/p/shirt-1">Link</a>
        <img src="/img/shirt.jpg" />
      </li>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, [])
    assert len(products) == 1
    assert products[0].item_image_link == "https://www.abercrombie.com/img/shirt.jpg"


def test_abercrombie_parse_html_drills_down_to_valid_image_when_first_is_placeholder() -> None:
    html = """
    <div>
      <li data-testid="catalog-product-card">
        <span data-testid="catalog-product-card-name">Shirt Name</span>
        <span data-testid="product-price">$29.00</span>
        <a href="/p/shirt-1">Link</a>
        <img src="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw" />
        <img src="/img/shirt-real.jpg" />
      </li>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, ["Womens", "Tops"])
    assert len(products) == 1
    assert products[0].item_image_link == "https://www.abercrombie.com/img/shirt-real.jpg"


def test_abercrombie_parse_html_uses_intlkic_when_only_placeholder_src() -> None:
    html = """
    <div>
      <li data-testid="catalog-product-card" data-intlkic="KIC_116-6033-00102-900">
        <span data-testid="catalog-product-card-name">Shirt Name</span>
        <span data-testid="product-price">$29.00</span>
        <a href="/p/shirt-1">Link</a>
        <img src="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw" />
      </li>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, ["Womens", "Tops"])
    assert len(products) == 1
    assert (
        products[0].item_image_link
        == "https://img.abercrombie.com/is/image/anf/KIC_116-6033-00102-900_prod1?policy=product-medium"
    )
