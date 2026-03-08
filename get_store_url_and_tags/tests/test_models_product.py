"""Tests for models.product."""

from get_store_url_and_tags.models.product import Product


def test_product_construction() -> None:
    p = Product(
        store="Abercrombie",
        item_name="Cool Shirt",
        item_image_link="https://example.com/img.jpg",
        item_link="https://example.com/p/1",
        price="$39.00",
        tags=["Mens", "T-Shirts"],
    )
    assert p.store == "Abercrombie"
    assert p.item_name == "Cool Shirt"
    assert p.item_image_link == "https://example.com/img.jpg"
    assert p.item_link == "https://example.com/p/1"
    assert p.price == "$39.00"
    assert p.tags == ["Mens", "T-Shirts"]
