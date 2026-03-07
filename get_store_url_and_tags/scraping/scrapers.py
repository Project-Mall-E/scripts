from typing import List
from bs4 import BeautifulSoup
from .base import BaseScraper
from .product import Product

class AbercrombieScraper(BaseScraper):
    def __init__(self):
        super().__init__("Abercrombie")
        self.base_url = "https://www.abercrombie.com"

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        products = []
        cards = soup.find_all("li", class_=lambda c: c and 'productCard-module__productCard' in c)
        
        for card in cards:
            name_elements = card.find_all(lambda tag: tag.has_attr('data-cmp') and tag['data-cmp'] == 'productName')
            name = "None"
            for el in name_elements:
                text = el.text.strip()
                if text and not "Activating this element" in text:
                    name = text.split('\n')[0].strip()
                    break
                    
            if name == "None":
                for a in card.find_all("a"):
                    a_text = a.text.strip()
                    if a_text and not "Activating this element" in a_text and len(a_text) > 3:
                        name = a_text.split('\n')[0].strip()
                        break
            
            price_elem = card.find("span", class_=lambda c: c and 'price' in c.lower() and not 'original' in c.lower() and not 'discount' in c.lower())
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
                
            # If the link is relative, prepend base_url
            if link != 'None' and link.startswith('/'):
                link = self.base_url + link
                
            # Avoid empty products where main items might have been missed
            if name != "None" and price != "None":
                products.append(Product(
                    store=self.store_name,
                    item_name=name,
                    item_image_link=img,
                    item_link=link,
                    price=price,
                    tags=tags
                ))
        return products

class AmericanEagleScraper(BaseScraper):
    def __init__(self):
        super().__init__("AmericanEagle")
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
            img_elem = card.find("img")

            name = name_elem.text.strip() if name_elem else 'None'
            price = price_elem.text.strip() if price_elem else 'None'

            link = link_elem['href'] if link_elem and link_elem.has_attr('href') else 'None'
            img = img_elem['src'] if img_elem and img_elem.has_attr('src') else 'None'
            
            if link != 'None' and link.startswith('/'):
                link = self.base_url + link
            
            if img != 'None' and img.startswith('//'):
                img = 'https:' + img
                
            if name != "None": # AE prices can sometimes be missing or in sub-spans, but we want the product
                products.append(Product(
                    store=self.store_name,
                    item_name=name,
                    item_image_link=img,
                    item_link=link,
                    price=price,
                    tags=tags
                ))
        return products

def get_scraper_for_store(store_name: str) -> BaseScraper:
    if store_name == "Abercrombie":
        return AbercrombieScraper()
    elif store_name == "AmericanEagle":
        return AmericanEagleScraper()
    else:
        # We don't have scrapers for all stores yet. Return a generic or ignore.
        return None
