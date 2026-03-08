"""Tests for tagging.rules."""

import pytest

from get_store_url_and_tags.tagging.rules import TAG_RULES, TagExtractor


def test_tag_extractor_default_rules() -> None:
    extractor = TagExtractor()
    assert extractor.rules is TAG_RULES
    assert extractor._compiled_patterns


def test_tag_extractor_custom_rules() -> None:
    rules = {
        "gender": {"Womens": ["women", "womens"]},
        "category": {"Tops": ["tops"]},
        "occasion": {},
    }
    extractor = TagExtractor(rules=rules)
    assert extractor.rules is rules
    result = extractor.extract_from_text("women tops")
    assert "gender" in result
    assert "Womens" in result["gender"]
    assert "category" in result
    assert "Tops" in result["category"]


def test_extract_from_text_empty() -> None:
    extractor = TagExtractor()
    assert extractor.extract_from_text("") == {}
    assert extractor.extract_from_text(None) == {}


def test_extract_from_text_gender() -> None:
    extractor = TagExtractor()
    result = extractor.extract_from_text("womens collection")
    assert "gender" in result
    assert "Womens" in result["gender"]


def test_extract_from_text_category() -> None:
    extractor = TagExtractor()
    result = extractor.extract_from_text("jeans and tops")
    assert "category" in result
    assert "Jeans" in result["category"]
    assert "Tops" in result["category"]


def test_extract_from_text_occasion() -> None:
    extractor = TagExtractor()
    result = extractor.extract_from_text("sale clearance")
    assert "occasion" in result
    assert "Sale" in result["occasion"]


def test_extract_from_text_case_insensitive() -> None:
    extractor = TagExtractor()
    result = extractor.extract_from_text("WOMENS TOPS")
    assert "Womens" in result.get("gender", set())
    assert "Tops" in result.get("category", set())


def test_extract_url_segments() -> None:
    extractor = TagExtractor()
    # _extract_url_segments is used inside extract(); path with /cat123 stripped
    text = extractor._extract_url_segments("https://example.com/womens/cat123/tops")
    assert "womens" in text
    assert "tops" in text
    assert "cat123" not in text


def test_extract_url_segments_clr_stripped() -> None:
    extractor = TagExtractor()
    text = extractor._extract_url_segments("https://example.com/clrABC123/dresses")
    assert "dresses" in text
    assert "clr" not in text or "clrabc" not in text.lower()


def test_extract_url_only() -> None:
    extractor = TagExtractor()
    result = extractor.extract(
        url="https://example.com/womens/jeans",
        nav_text=None,
        page_title=None,
        breadcrumb_text=None,
    )
    assert "Womens" in result or "Jeans" in result
    assert isinstance(result, list)


def test_extract_nav_text() -> None:
    extractor = TagExtractor()
    result = extractor.extract(
        url="https://example.com/other",
        nav_text="Women Tops",
        page_title=None,
        breadcrumb_text=None,
    )
    assert "Womens" in result or "Tops" in result


def test_extract_page_title() -> None:
    extractor = TagExtractor()
    result = extractor.extract(
        url="https://example.com/x",
        nav_text=None,
        page_title="Sale Clearance",
        breadcrumb_text=None,
    )
    assert "Sale" in result


def test_extract_breadcrumb() -> None:
    extractor = TagExtractor()
    result = extractor.extract(
        url="https://example.com/x",
        nav_text=None,
        page_title=None,
        breadcrumb_text="Home / Women / Dresses",
    )
    assert "Womens" in result or "Dresses" in result


def test_extract_merges_sources() -> None:
    extractor = TagExtractor()
    result = extractor.extract(
        url="https://example.com/womens",
        nav_text="Tops",
        page_title="Sale",
        breadcrumb_text="Casual",
    )
    # Should have tags from multiple dimensions (gender, category, occasion)
    assert len(result) >= 2
    assert "Womens" in result or "Tops" in result
    assert "Sale" in result or "Casual" in result


def test_normalize_text() -> None:
    extractor = TagExtractor()
    out = extractor._normalize_text("  Women's  Tops  ")
    assert "women" in out
    assert "tops" in out
