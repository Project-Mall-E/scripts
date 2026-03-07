"""Abercrombie product listing scraper."""

from typing import List
from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..product import Product

STORE_NAME = "Abercrombie"


class AbercrombieScraper(BaseScraper):
    def __init__(self):
        super().__init__(STORE_NAME)
        self.base_url = "https://www.abercrombie.com"

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        products = []
        cards = soup.find_all("li", class_=lambda c: c and 'productCard-module__productCard' in c)

        for card in cards:
            name_elements = card.find_all(lambda tag: tag.has_attr('data-cmp') and tag['data-cmp'] == 'productName')
            name = "None"
            for el in name_elements:
                text = el.text.strip()
                if text and "Activating this element" not in text:
                    name = text.split('\n')[0].strip()
                    break

            if name == "None":
                for a in card.find_all("a"):
                    a_text = a.text.strip()
                    if a_text and "Activating this element" not in a_text and len(a_text) > 3:
                        name = a_text.split('\n')[0].strip()
                        break

            price_elem = card.find("span", class_=lambda c: c and 'price' in c.lower() and 'original' not in c.lower() and 'discount' not in c.lower())
            if not price_elem:
                price_elem = card.find(lambda tag: tag.has_attr('data-cmp') and 'price' in tag['data-cmp'].lower())

            link_elem = card.find("a", class_=lambda c: c and 'link' in c.lower())
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
