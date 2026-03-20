"""Abercrombie product listing scraper."""

from typing import List
from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..card_descriptions import collect_item_descriptions_from_card
from ..product import Product

STORE_NAME = "Abercrombie"

# Common 1x1 tracking pixel used by some sites in <img src="...">.
# Keeping it would later fail any "valid image" check/downloader.
_PLACEHOLDER_1X1_GIF_DATA_URI_BASE64 = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw"


def _is_placeholder_1x1_gif_data_uri(src: str) -> bool:
    if not src:
        return False
    s = src.strip()
    return (
        s.startswith("data:image/gif;base64,")
        and _PLACEHOLDER_1X1_GIF_DATA_URI_BASE64 in s
    )


def _is_usable_abercrombie_cdn_image(url: str) -> bool:
    """
    Omit Scene7 URLs that are not meaningful product photography on a listing card:
    policy=product-xsmall thumbnails and *_sw swatch variants.
    """
    if "img.abercrombie.com/is/image/anf/" not in url:
        return True
    if "policy=product-xsmall" in url.lower():
        return False
    path = url.split("?", 1)[0]
    asset = path.rsplit("/", 1)[-1]
    if asset.endswith("_sw"):
        return False
    return True


def _normalize_image_src(src: str, *, base_url: str) -> str:
    """
    Normalize image URL.
    Returns "None" when the URL is unusable (placeholder, empty, etc.).
    """
    if not src:
        return "None"
    s = src.strip()
    if _is_placeholder_1x1_gif_data_uri(s):
        return "None"
    if s.startswith("//"):
        return "https:" + s
    if s.startswith("/"):
        return base_url + s
    return s


def _image_url_from_intlkic(intlkic: str) -> str | None:
    """
    Build an Abercrombie image URL from the product card's data-intlkic id.
    Example intlkic: "KIC_116-6054-00163-380".
    """
    if not intlkic:
        return None
    kic = intlkic.strip()
    # On Abercrombie listing pages, when the visible <img> only contains a
    # 1x1 placeholder, the real image is typically served under the `_prod1`
    # variant (not `_model1`). Prefer `_prod1` for that fallback.
    #
    # If the id already includes a suffix, keep it as-is.
    if "_prod" in kic or "_model" in kic:
        image_id = kic
    else:
        image_id = f"{kic}_prod1"
    return (
        "https://img.abercrombie.com/is/image/anf/"
        f"{image_id}?policy=product-medium"
    )


def _class_contains(classes, substring: str, case_sensitive: bool = True) -> bool:
    """Match when any class token contains substring (handles BS4 class as list or str)."""
    if not classes:
        return False
    sub = substring if case_sensitive else substring.lower()
    if isinstance(classes, list):
        return any(
            (sub in (c or "")) if case_sensitive else (sub in (c or "").lower())
            for c in classes
        )
    s = classes or ""
    return sub in s if case_sensitive else sub in s.lower()


def _product_name_only(raw: str) -> str:
    """Extract product name by dropping price/promo text (e.g. $14.95, Price After 25% Off)."""
    if not raw or "Activating this element" in raw:
        return ""
    first_line = raw.split("\n")[0].strip()
    # Card link text is often "name$14.95$11.21Price After 25% Off..."; keep only the name.
    for sep in ("$", "Price ", "price "):
        idx = first_line.find(sep)
        if idx != -1:
            first_line = first_line[:idx]
    return first_line.strip()


class AbercrombieScraper(BaseScraper):
    def __init__(self):
        super().__init__(STORE_NAME)
        self.base_url = "https://www.abercrombie.com"

    def content_ready_selector(self) -> str | None:
        """Catalog is JS-rendered; wait for product cards to appear (testid or class)."""
        return '[data-testid="catalog-product-card"], li[class*="productCard-module__productCard"]'

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        products = []
        # Prefer stable data-testid; fall back to li with productCard class (handles prefixed classes)
        cards = soup.find_all(attrs={"data-testid": "catalog-product-card"})
        if not cards:
            cards = soup.find_all("li", class_=lambda c: _class_contains(c, "productCard-module__productCard"))

        for card in cards:
            name = None
            # Prefer data-testid (stable); then h2; then class product-name
            name_el = (
                card.find(attrs={"data-testid": "catalog-product-card-name"})
                or card.find("h2")
                or card.find(class_=lambda c: _class_contains(c, "product-name"))
            )
            if name_el:
                name = name_el.get_text(strip=True)
            # Reject accessibility/screen-reader placeholder text from any source
            if name and "Activating this element" in name:
                name = None
            if not name:
                el = card.find(lambda tag: tag.has_attr("data-cmp") and tag.get("data-cmp") == "productName")
                if el:
                    name = _product_name_only(el.get_text())
            # Fallback: use the product link's text (one get_text instead of iterating all <a>).
            if not name:
                _link = card.find("a", class_=lambda c: _class_contains(c, "link", case_sensitive=False)) or card.find("a")
                if _link:
                    _raw = _product_name_only(_link.get_text())
                    if _raw and len(_raw) > 3:
                        name = _raw
            if not name:
                name = "None"
            name = name.replace("New!", "")


            price_elem = card.find(attrs={"data-testid": "product-price"})
            if not price_elem:
                price_elem = card.find("span", class_=lambda c: _class_contains(c, "price", case_sensitive=False) and not _class_contains(c, "original") and not _class_contains(c, "discount"))
            if not price_elem:
                price_elem = card.find(lambda tag: tag.has_attr("data-cmp") and "price" in (tag.get("data-cmp") or "").lower())

            link_elem = card.find("a", class_=lambda c: _class_contains(c, "link", case_sensitive=False))
            if not link_elem:
                link_elem = card.find("a")

            # Image sources: some pages include placeholder tracking pixels (1x1 GIF data URIs)
            # before the real product image. We collect every non-placeholder <img> URL in DOM
            # order, then dedupe.
            img_candidates: list[str] = []
            for img_tag in card.find_all("img"):
                if img_tag.has_attr("src"):
                    img_candidates.append(img_tag["src"])

            price = price_elem.text.strip() if price_elem else 'None'
            if "$" in price and len(price) > 3:
                parts = price.split("$")
                if len(parts) > 2 and parts[1] == parts[2]:
                    price = f"${parts[1]}"

            link = link_elem['href'] if link_elem and link_elem.has_attr('href') else 'None'
            collected: list[str] = []
            for candidate in img_candidates:
                normalized = _normalize_image_src(candidate, base_url=self.base_url)
                if normalized != "None" and _is_usable_abercrombie_cdn_image(normalized):
                    collected.append(normalized)
            item_image_links = list(dict.fromkeys(collected))

            # Some pages render only a 1x1 placeholder in <img src="..."> and
            # rely on JS to resolve real imagery. In that case, use the card's
            # data-intlkic to reconstruct a deterministic image URL.
            if not item_image_links:
                intlkic = card.get("data-intlkic")
                if intlkic:
                    fallback = _image_url_from_intlkic(intlkic)
                    if fallback:
                        item_image_links = [fallback]

            if link != 'None' and link.startswith('/'):
                link = self.base_url + link

            if name != 'None' and price != "None":
                item_descriptions = collect_item_descriptions_from_card(card, name)
                products.append(Product(
                    store=self.store_name,
                    item_name=name,
                    item_image_links=item_image_links,
                    item_link=link,
                    price=price,
                    tags=tags,
                    item_descriptions=item_descriptions,
                ))
        return products
