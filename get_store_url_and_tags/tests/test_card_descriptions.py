"""Tests for scraping.card_descriptions."""

from bs4 import BeautifulSoup

from get_store_url_and_tags.scraping.card_descriptions import (
    collect_item_descriptions_from_card,
)


def test_collect_from_data_qa_color() -> None:
    html = """
    <div data-qa="product-card">
      <span data-qa="product-card-color">Optic White</span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "Relaxed Jeans") == [
        "optic",
        "white",
    ]


def test_collect_dedupes_and_preserves_order() -> None:
    html = """
    <div>
      <span data-qa="subtitle">Slim Fit</span>
      <span data-testid="swatch-label">Navy</span>
      <span data-qa="subtitle">Slim Fit</span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "Chinos") == [
        "slim",
        "fit",
        "navy",
    ]


def test_collect_skips_title_and_price_like_text() -> None:
    html = """
    <div>
      <span data-qa="product-color">Cool Shirt</span>
      <span data-qa="fabric-hint">$29.99</span>
      <span data-qa="fabric-hint">Cotton</span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "Cool Shirt") == ["cotton"]


def test_collect_from_class_subtitle() -> None:
    html = """
    <div>
      <p class="product-card-subtitle">High Rise</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "Shorts") == ["high", "rise"]


def test_collect_from_data_cmp() -> None:
    html = """
    <div>
      <span data-cmp="productFabricDetail">Linen blend</span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "Dress") == ["linen", "blend"]


def test_collect_drops_swatch_noise_tokens() -> None:
    html = """
    <div>
      <span data-qa="color-swatch">Flint swatch</span>
      <span data-qa="color-swatch">Light Gray swatch</span>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "Pants") == ["flint", "light", "gray"]


def test_collect_merchant_flags_data_testid() -> None:
    html = """
    <div>
      <div data-testid="merchant-flags">New</div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "Some Product") == ["new"]


def test_merge_unique_word_lists_order() -> None:
    from get_store_url_and_tags.scraping.card_descriptions import merge_unique_word_lists

    assert merge_unique_word_lists(["a", "b"], ["b", "c"]) == ["a", "b", "c"]


def test_collect_hyphenated_word_stays_single_token() -> None:
    html = """
    <div>
      <p class="product-card-subtitle">open-hem leg</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    card = soup.find("div")
    assert collect_item_descriptions_from_card(card, "X") == ["open-hem", "leg"]
