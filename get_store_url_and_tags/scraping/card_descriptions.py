"""Extract facet-like words (color, fit, fabric, etc.) from listing card DOM."""

from __future__ import annotations

import re
from typing import Any

# Tokens matched in order; hyphenated / apostrophe compounds stay one token.
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:['-][a-zA-Z0-9]+)*")

# Listing chrome that is not useful for cross-store search.
_NOISE_TOKENS: frozenset[str] = frozenset({"swatch", "swatches"})

# Match data-qa / data-testid / data-cmp attribute values containing these substrings.
_ATTR_HINT_SUBSTRINGS: tuple[str, ...] = (
    "subtitle",
    "color",
    "swatch",
    "fabric",
    "fit",
    "inseam",
    "length",
    "rise",
    "material",
    "wash",
    "descriptor",
    "colorway",
    "hem",
    "neck",
    "sleev",
    "merchant",
)

# class= tokens (substring match on joined classes)
_CLASS_HINT_SUBSTRINGS: tuple[str, ...] = (
    "subtitle",
    "colorway",
    "descriptor",
    "product-card-subtitle",
    "productcolor",
    "product-color",
    "swatch-label",
    "color-name",
)


def _classes_to_lowercase_string(classes: Any) -> str:
    if not classes:
        return ""
    if isinstance(classes, list):
        return " ".join((c or "").lower() for c in classes)
    return str(classes).lower()


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _unique_word_tokens(phrases: list[str]) -> list[str]:
    """
    Flatten phrase strings into unique lowercase words; first-seen order preserved.
    """
    seen: set[str] = set()
    out: list[str] = []
    for phrase in phrases:
        for m in _TOKEN_RE.finditer(phrase.lower()):
            w = m.group(0).strip("'")
            if len(w) < 2 or w in _NOISE_TOKENS:
                continue
            if w not in seen:
                seen.add(w)
                out.append(w)
    return out


def _is_usable_descriptor(text: str, item_name_norm: str) -> bool:
    t = _normalize(text)
    if len(t) < 2:
        return False
    if t.lower() == item_name_norm:
        return False
    if t.startswith("$"):
        return False
    if "$" in t and any(c.isdigit() for c in t):
        return False
    return True


def collect_item_descriptions_from_card(card: Any, item_name: str) -> list[str]:
    """
    Gather facet text from the card when the DOM exposes it, then split into
    unique lowercase words (order preserved, first occurrence wins).
    """
    item_name_norm = (item_name or "").strip().lower()
    candidates: list[str] = []

    for el in card.find_all(True):
        for attr in ("data-qa", "data-testid"):
            if not el.has_attr(attr):
                continue
            val = (el.get(attr) or "").lower()
            if not any(h in val for h in _ATTR_HINT_SUBSTRINGS):
                continue
            t = _normalize(el.get_text(separator=" ", strip=True))
            if _is_usable_descriptor(t, item_name_norm):
                candidates.append(t)

    for el in card.find_all(class_=True):
        cls = _classes_to_lowercase_string(el.get("class"))
        if not cls:
            continue
        if not any(sub in cls for sub in _CLASS_HINT_SUBSTRINGS):
            continue
        t = _normalize(el.get_text(separator=" ", strip=True))
        if _is_usable_descriptor(t, item_name_norm):
            candidates.append(t)

    for el in card.find_all(attrs={"data-cmp": True}):
        cmp_val = (el.get("data-cmp") or "").lower()
        if not any(h in cmp_val for h in _ATTR_HINT_SUBSTRINGS):
            continue
        t = _normalize(el.get_text(separator=" ", strip=True))
        if _is_usable_descriptor(t, item_name_norm):
            candidates.append(t)

    return _unique_word_tokens(list(dict.fromkeys(candidates)))


def unique_words_from_texts(texts: list[str]) -> list[str]:
    """Lowercase unique words from raw strings (same token rules as card extraction)."""
    return _unique_word_tokens(texts)


def merge_unique_word_lists(*parts: list[str]) -> list[str]:
    """First-seen unique words across lists: all of list1 in order, then new from list2, …"""
    seen: set[str] = set()
    out: list[str] = []
    for lst in parts:
        for w in lst:
            if w not in seen:
                seen.add(w)
                out.append(w)
    return out
