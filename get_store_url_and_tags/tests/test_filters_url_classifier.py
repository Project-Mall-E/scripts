"""Tests for filters.url_classifier."""

import pytest

from get_store_url_and_tags.filters.url_classifier import URLClassifier


def test_classifier_constructor() -> None:
    c = URLClassifier(
        extra_category_patterns=[r"/extra/"],
        extra_exclude_patterns=[r"/exclude/"],
        max_path_depth=3,
    )
    assert c._max_path_depth == 3


def test_is_category_url_invalid_empty() -> None:
    c = URLClassifier()
    assert c.is_category_url("") is False
    assert c.is_category_url(None) is False


def test_is_category_url_not_http() -> None:
    c = URLClassifier()
    assert c.is_category_url("ftp://example.com/womens") is False
    assert c.is_category_url("example.com/womens") is False


def test_is_category_url_excluded_extension() -> None:
    c = URLClassifier()
    assert c.is_category_url("https://example.com/page.pdf") is False
    assert c.is_category_url("https://example.com/image.jpg") is False
    assert c.is_category_url("https://example.com/script.js") is False


def test_is_category_url_fragment_or_query_only() -> None:
    c = URLClassifier()
    base = "https://example.com/"
    assert c.is_category_url("https://example.com/#section", base) is False
    assert c.is_category_url("https://example.com/", base) is False


def test_is_category_url_path_prefix_mismatch() -> None:
    c = URLClassifier()
    base = "https://example.com/en"
    assert c.is_category_url("https://example.com/fr/womens", base) is False


def test_is_category_url_max_path_depth() -> None:
    c = URLClassifier(max_path_depth=2)
    base = "https://example.com/"
    # /a/b/c has 3 segments
    assert c.is_category_url("https://example.com/a/b/c/womens", base) is False


def test_is_category_url_exclude_pattern() -> None:
    c = URLClassifier()
    assert c.is_category_url("https://example.com/login") is False
    assert c.is_category_url("https://example.com/cart") is False
    assert c.is_category_url("https://example.com/account") is False


def test_is_category_url_category_match() -> None:
    c = URLClassifier()
    assert c.is_category_url("https://example.com/womens/tops") is True
    assert c.is_category_url("https://example.com/shop/jeans") is True
    assert c.is_category_url("https://example.com/collection/sale") is True


def test_is_category_url_no_match() -> None:
    c = URLClassifier()
    assert c.is_category_url("https://example.com/random/page") is False


def test_is_category_url_strips_fragment_before_check() -> None:
    c = URLClassifier()
    # URL with # still has /womens/ in path so can match
    assert c.is_category_url("https://example.com/womens/tops#section") is True


def test_filter_category_urls_deduplication() -> None:
    c = URLClassifier()
    urls = [
        "https://example.com/womens/tops",
        "https://example.com/womens/tops/",
        "https://example.com/womens/tops#x",
    ]
    result = c.filter_category_urls(urls)
    assert len(result) == 1


def test_filter_category_urls_mixed() -> None:
    c = URLClassifier()
    urls = [
        "https://example.com/womens/tops",
        "https://example.com/login",
        "https://example.com/mens/jeans",
    ]
    result = c.filter_category_urls(urls)
    assert len(result) == 2
    assert "https://example.com/womens/tops" in result
    assert "https://example.com/mens/jeans" in result
    assert "https://example.com/login" not in result


def test_filter_category_urls_empty() -> None:
    c = URLClassifier()
    assert c.filter_category_urls([]) == []
