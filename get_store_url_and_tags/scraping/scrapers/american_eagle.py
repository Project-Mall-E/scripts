"""American Eagle product listing scraper."""

from typing import List
from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..product import Product

STORE_NAME = "AmericanEagle"


def _collect_image_links(card) -> list[str]:
    """Normalize and dedupe image URLs from the card, DOM order preserved."""
    urls: list[str] = []
    for img_elem in card.find_all("img"):
        if not img_elem.has_attr("src"):
            continue
        src = (img_elem["src"] or "").strip()
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        urls.append(src)
    return list(dict.fromkeys(urls))


class AmericanEagleScraper(BaseScraper):
    def __init__(self):
        super().__init__(STORE_NAME)
        self.base_url = "https://www.ae.com"

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        products = []
        cards = soup.find_all("div", attrs={"data-qa": "product-card"})
        if not cards:
            cards = soup.find_all("div", class_=lambda c: c and 'product-tile' in c.lower())

        for card in cards:
            name_elem = card.find("h3") or card.find("h2") or card.find("div", class_=lambda c: c and 'name' in c.lower())

            price_elem = card.find("div", attrs={"data-qa": "price"})
            if not price_elem:
                price_elem = card.find(attrs={"data-testid": "sale-price"})
            if not price_elem:
                price_elem = card.find(attrs={"data-testid": "list-price"})
            if not price_elem:
                price_elem = card.find("span", class_=lambda c: c and 'price' in c.lower())
            if not price_elem:
                price_elem = card.find("div", class_=lambda c: c and 'price' in c.lower())

            link_elem = card.find("a")

            name = name_elem.text.strip() if name_elem else 'None'
            price = price_elem.text.strip() if price_elem else 'None'

            link = link_elem['href'] if link_elem and link_elem.has_attr('href') else 'None'
            item_image_links = _collect_image_links(card)

            if link != 'None' and link.startswith('/'):
                link = self.base_url + link

            if name != "None":
                products.append(Product(
                    store=self.store_name,
                    item_name=name,
                    item_image_links=item_image_links,
                    item_link=link,
                    price=price,
                    tags=tags
                ))
        return products
