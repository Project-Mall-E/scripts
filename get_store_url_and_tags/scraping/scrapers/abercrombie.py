"""Abercrombie product listing scraper."""

from typing import List
from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..product import Product

STORE_NAME = "Abercrombie"


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

            img_elem = card.find("img")

            price = price_elem.text.strip() if price_elem else 'None'
            if "$" in price and len(price) > 3:
                parts = price.split("$")
                if len(parts) > 2 and parts[1] == parts[2]:
                    price = f"${parts[1]}"

            link = link_elem['href'] if link_elem and link_elem.has_attr('href') else 'None'
            img = img_elem['src'] if img_elem and img_elem.has_attr('src') else 'None'
            if img == 'None' and link_elem and link_elem.find("img"):
                img = link_elem.find("img")['src']

            if link != 'None' and link.startswith('/'):
                link = self.base_url + link

            if name != 'None' and price != "None":
                products.append(Product(
                    store=self.store_name,
                    item_name=name,
                    item_image_link=img,
                    item_link=link,
                    price=price,
                    tags=tags
                ))
        return products
