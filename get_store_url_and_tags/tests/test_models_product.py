"""Tests for models.product."""

from get_store_url_and_tags.models.product import Product


def test_product_construction() -> None:
    p = Product(
        store="Abercrombie",
        item_name="Cool Shirt",
        item_image_links=["https://example.com/img.jpg"],
        item_link="https://example.com/p/1",
        price="$39.00",
        tags=["Mens", "T-Shirts"],
    )
    assert p.store == "Abercrombie"
    assert p.item_name == "Cool Shirt"
    assert p.item_image_links == ["https://example.com/img.jpg"]
    assert p.item_link == "https://example.com/p/1"
    assert p.price == "$39.00"
    assert p.tags == ["Mens", "T-Shirts"]


def test_product_empty_image_links() -> None:
    p = Product(
        store="S",
        item_name="X",
        item_image_links=[],
        item_link="https://x",
        price="$1",
        tags=[],
    )
    assert p.item_image_links == []
    assert p.item_descriptions == []


def test_product_item_descriptions_explicit() -> None:
    p = Product(
        store="S",
        item_name="Pants",
        item_image_links=[],
        item_link="https://x",
        price="$1",
        tags=["Womens", "Pants"],
        item_descriptions=["white", "wide", "leg"],
    )
    assert p.item_descriptions == ["white", "wide", "leg"]
