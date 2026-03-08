"""Tests for models.links."""

from get_store_url_and_tags.models.links import StoreLink


def test_store_link_construction() -> None:
    link = StoreLink(
        name="AmericanEagle",
        url="https://www.ae.com/womens/jeans",
        tags=["Womens", "Jeans"],
    )
    assert link.name == "AmericanEagle"
    assert link.url == "https://www.ae.com/womens/jeans"
    assert link.tags == ["Womens", "Jeans"]
