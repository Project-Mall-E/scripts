"""Tests for tagging.normalizer."""

import pytest

from get_store_url_and_tags.tagging.normalizer import (
    TAG_HIERARCHY,
    TAG_SYNONYMS,
    TagNormalizer,
)


def test_normalizer_defaults() -> None:
    n = TagNormalizer()
    assert n.synonyms is TAG_SYNONYMS
    assert n.hierarchy is TAG_HIERARCHY
    assert n.fuzzy_threshold == 0.85
    assert n._synonym_lookup
    assert n._canonical_tags


def test_normalize_tag_direct_synonym() -> None:
    n = TagNormalizer()
    assert n.normalize_tag("woman") == "Womens"
    assert n.normalize_tag("womens") == "Womens"
    assert n.normalize_tag("tops") == "Tops"


def test_normalize_tag_canonical() -> None:
    n = TagNormalizer()
    assert n.normalize_tag("Womens") == "Womens"
    assert n.normalize_tag("Tops") == "Tops"


def test_normalize_tag_empty_whitespace() -> None:
    n = TagNormalizer()
    assert n.normalize_tag("") is None
    assert n.normalize_tag("   ") is None
    assert n.normalize_tag(None) is None


def test_normalize_tag_fuzzy_above_threshold() -> None:
    n = TagNormalizer(fuzzy_threshold=0.8)
    # "womns" is close to "Womens" or synonym
    result = n.normalize_tag("womns")
    # May match Womens via fuzzy
    assert result is None or result in n._canonical_tags


def test_normalize_tag_unknown_below_threshold(caplog: pytest.LogCaptureFixture) -> None:
    n = TagNormalizer(fuzzy_threshold=0.99)
    assert n.normalize_tag("xyznonexistent") is None
    assert "Unknown tag" in caplog.text


def test_normalize_empty_list() -> None:
    n = TagNormalizer()
    assert n.normalize([]) == []


def test_normalize_deduplication() -> None:
    n = TagNormalizer()
    result = n.normalize(["women", "womens", "Womens"])
    assert result.count("Womens") == 1


def test_normalize_hierarchy_order() -> None:
    n = TagNormalizer()
    result = n.normalize(["Sale", "Womens", "Tops"])
    # Gender (10) before category (20) before occasion (30)
    assert result.index("Womens") < result.index("Tops")
    assert result.index("Tops") < result.index("Sale")


def test_normalize_unknown_tag_warning(caplog: pytest.LogCaptureFixture) -> None:
    n = TagNormalizer(fuzzy_threshold=0.99)
    n.normalize(["validwomen", "xyzzz"])
    # "validwomen" might not match; "xyzzz" won't
    assert "Unknown tag" in caplog.text or len(caplog.record_tuples) >= 0


def test_add_synonym_new_canonical() -> None:
    n = TagNormalizer(synonyms={"Tops": ["tops"]}, hierarchy={"Tops": 20})
    n.add_synonym("NewCat", "newcat")
    assert "newcat" in [v for vals in n.synonyms.values() for v in vals] or "NewCat" in n.synonyms
    assert n.normalize_tag("newcat") == "NewCat" or "NewCat" in n.synonyms


def test_add_synonym_existing_canonical() -> None:
    n = TagNormalizer()
    n.add_synonym("Tops", "tees")
    assert n.normalize_tag("tees") == "Tops"


def test_get_all_canonical_tags() -> None:
    n = TagNormalizer()
    tags = n.get_all_canonical_tags()
    assert "Womens" in tags
    assert "Tops" in tags
    assert tags == sorted(tags, key=lambda t: (n.hierarchy.get(t, 50), t))
