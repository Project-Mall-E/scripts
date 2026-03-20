"""Tests for scraping.scrapers.abercrombie."""

from bs4 import BeautifulSoup

from get_store_url_and_tags.scraping.scrapers.abercrombie import (
    AbercrombieScraper,
    _class_contains,
    _is_usable_abercrombie_cdn_image,
    _product_name_only,
)


def test_is_usable_abercrombie_cdn_image_non_cdn_always_ok() -> None:
    assert _is_usable_abercrombie_cdn_image("https://www.abercrombie.com/img/x.jpg") is True


def test_is_usable_abercrombie_cdn_image_rejects_xsmall_policy() -> None:
    assert (
        _is_usable_abercrombie_cdn_image(
            "https://img.abercrombie.com/is/image/anf/KIC_1_prod1?policy=product-xsmall"
        )
        is False
    )


def test_is_usable_abercrombie_cdn_image_rejects_sw_swatch_even_with_medium() -> None:
    u = "https://img.abercrombie.com/is/image/anf/KIC_116-6064-00186-221_sw?policy=product-medium"
    assert _is_usable_abercrombie_cdn_image(u) is False


def test_is_usable_abercrombie_cdn_image_accepts_prod_medium() -> None:
    u = "https://img.abercrombie.com/is/image/anf/KIC_116-6063-00185-401_prod1?policy=product-medium"
    assert _is_usable_abercrombie_cdn_image(u) is True


def test_abercrombie_parse_html_skips_xsmall_and_swatch_cdn_urls() -> None:
    html = """
    <li data-testid="catalog-product-card">
      <span data-testid="catalog-product-card-name">Shorts</span>
      <span data-testid="product-price">$65</span>
      <a href="/p/1">L</a>
      <img src="https://img.abercrombie.com/is/image/anf/KIC_116-6063-00185-401_prod1?policy=product-medium" />
      <img src="https://img.abercrombie.com/is/image/anf/KIC_116-6064-00186-221_sw?policy=product-xsmall" />
      <img src="https://img.abercrombie.com/is/image/anf/KIC_116-6063-00185-401_sw?policy=product-xsmall" />
    </li>
    """
    soup = BeautifulSoup(html, "html.parser")
    products = AbercrombieScraper().parse_html(soup, [])
    assert len(products) == 1
    assert products[0].item_image_links == [
        "https://img.abercrombie.com/is/image/anf/KIC_116-6063-00185-401_prod1?policy=product-medium",
    ]


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
        <span data-testid="catalog-product-card-color">Heather Gray</span>
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
    assert products[0].item_descriptions == ["heather", "gray"]
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
    assert products[0].item_image_links == []


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
    assert products[0].item_image_links == [
        "https://www.abercrombie.com/img/shirt.jpg",
    ]


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
    assert products[0].item_image_links == [
        "https://www.abercrombie.com/img/shirt-real.jpg",
    ]


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
    assert products[0].item_image_links == [
        "https://img.abercrombie.com/is/image/anf/KIC_116-6033-00102-900_prod1?policy=product-medium",
    ]


def test_abercrombie_parse_html_collects_multiple_distinct_images() -> None:
    html = """
    <div>
      <li data-testid="catalog-product-card">
        <span data-testid="catalog-product-card-name">Shirt Name</span>
        <span data-testid="product-price">$29.00</span>
        <a href="/p/shirt-1">Link</a>
        <img src="/img/a.jpg" />
        <img src="/img/b.jpg" />
      </li>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, [])
    assert len(products) == 1
    assert products[0].item_image_links == [
        "https://www.abercrombie.com/img/a.jpg",
        "https://www.abercrombie.com/img/b.jpg",
    ]


def test_abercrombie_parse_html_dedupes_duplicate_image_urls() -> None:
    html = """
    <div>
      <li data-testid="catalog-product-card">
        <span data-testid="catalog-product-card-name">Shirt Name</span>
        <span data-testid="product-price">$29.00</span>
        <a href="/p/shirt-1">Link</a>
        <img src="/img/same.jpg" />
        <img src="/img/same.jpg" />
      </li>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    scraper = AbercrombieScraper()
    products = scraper.parse_html(soup, [])
    assert products[0].item_image_links == ["https://www.abercrombie.com/img/same.jpg"]
