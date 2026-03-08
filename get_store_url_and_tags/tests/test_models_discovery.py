"""Tests for models.discovery."""

from get_store_url_and_tags.models.discovery import DiscoveredURL


def test_discovered_url_construction() -> None:
    u = DiscoveredURL(
        url="https://example.com/cat",
        store_name="Store",
        nav_text="Cat",
        page_title="Category",
        breadcrumb_text="Home / Cat",
        discovery_method="sitemap",
        depth=1,
    )
    assert u.url == "https://example.com/cat"
    assert u.store_name == "Store"
    assert u.nav_text == "Cat"
    assert u.discovery_method == "sitemap"
    assert u.depth == 1


def test_discovered_url_eq_same_url() -> None:
    a = DiscoveredURL(url="https://a.com/p", store_name="S")
    b = DiscoveredURL(url="https://a.com/p", store_name="S", nav_text="X")
    assert a == b
    assert hash(a) == hash(b)


def test_discovered_url_eq_different_url() -> None:
    a = DiscoveredURL(url="https://a.com/p1", store_name="S")
    b = DiscoveredURL(url="https://a.com/p2", store_name="S")
    assert a != b
    assert hash(a) != hash(b)


def test_discovered_url_eq_non_discovered_url() -> None:
    u = DiscoveredURL(url="https://a.com/p", store_name="S")
    assert u != "https://a.com/p"
    assert u != None  # noqa: E711
