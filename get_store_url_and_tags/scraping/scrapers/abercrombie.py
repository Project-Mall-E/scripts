"""Abercrombie product listing scraper."""

from typing import List
from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..product import Product

STORE_NAME = "Abercrombie"


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

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        products = []
        cards = soup.find_all("li", class_=lambda c: c and 'productCard-module__productCard' in c)

        for card in cards:
            name = None
            # Prefer elements that contain only the product name (not the whole card link text).
            name_el = card.find("h2") or card.find(class_=lambda c: c and "product-name" in (c or ""))
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
                _link = card.find("a", class_=lambda c: c and "link" in (c or "").lower()) or card.find("a")
                if _link:
                    _raw = _product_name_only(_link.get_text())
                    if _raw and len(_raw) > 3:
                        name = _raw
            if not name:
                name = "None"
            name = name.replace("New!", "")


            price_elem = card.find("span", class_=lambda c: c and "price" in (c or "").lower() and "original" not in (c or "").lower() and "discount" not in (c or "").lower())
            if not price_elem:
                price_elem = card.find(lambda tag: tag.has_attr("data-cmp") and "price" in (tag.get("data-cmp") or "").lower())

            link_elem = card.find("a", class_=lambda c: c and "link" in (c or "").lower())
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
