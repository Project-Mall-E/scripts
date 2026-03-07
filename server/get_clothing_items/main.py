import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from typing import List

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from store_config import StoreConfig, STORE_CONFIG

# --- Scraper Architecture ---

class BaseScraper:
    def __init__(self, store_name: str):
        self.store_name = store_name
        self.base_url = ""

    async def scrape(self, page, url: str) -> List[Product]:
        """
        Navigates to the URL, waits for products to load, 
        and parses the HTML into Product objects.
        """
        print(f"[{self.store_name}] Navigating to {url} ...")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"[{self.store_name}] Page loaded. Waiting for any bot checks to complete...")
            time.sleep(5)
            # Add some scrolling to seem human
            for _ in range(3):
                await page.mouse.wheel(0, 500)
                time.sleep(1)
                
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            return self.parse_html(soup)
        except Exception as e:
            print(f"[{self.store_name}] Failed to scrape: {e}")
            return []

    def parse_html(self, soup: BeautifulSoup) -> List[Product]:
        """must be implemented by subclasses"""
        raise NotImplementedError


class AbercrombieScraper(BaseScraper):
    def __init__(self):
        super().__init__("Abercrombie")
        self.base_url = "https://www.abercrombie.com"

    def parse_html(self, soup: BeautifulSoup) -> List[Product]:
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
                    price=price
                ))
        return products

class AmericanEagleScraper(BaseScraper):
    def __init__(self):
        super().__init__("AmericanEagle")
        self.base_url = "https://www.ae.com"

    def parse_html(self, soup: BeautifulSoup) -> List[Product]:
        products = []
        cards = soup.find_all("div", attrs={"data-qa": "product-card"})
        if not cards:
            cards = soup.find_all("div", class_=lambda c: c and 'product-tile' in c.lower())

        for card in cards:
            name_elem = card.find("h3") or card.find("h2") or card.find("div", class_=lambda c: c and 'name' in c.lower())
            
            price_elem = card.find("div", attrs={"data-qa": "price"})
            if not price_elem:
                price_elem = card.find("span", class_=lambda c: c and 'price' in c.lower())
                
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
                    price=price
                ))
        return products

def get_scraper_for_store(store_name: str) -> BaseScraper:
    if store_name == "Abercrombie":
        return AbercrombieScraper()
    elif store_name == "AmericanEagle":
        return AmericanEagleScraper()
    else:
        raise ValueError(f"Unknown store: {store_name}")


# --- Main Application Logic ---

async def get_products_by_category(category_path: str) -> List[Product]:
    category_tags = category_path.split("/")
    
    stores_to_scrape = [
        config for config in STORE_CONFIG 
        if config.tags == category_tags
    ]

    if not stores_to_scrape:
        print(f"Error: Category '{category_path}' not found in configuration.")
        print("Available categories:")
        seen_paths = set()
        for config in STORE_CONFIG:
            path = "/".join(config.tags)
            if path not in seen_paths:
                print(f"  - {path}")
                seen_paths.add(path)
        return []

    all_products = []

    async with async_playwright() as p:
        # NOTE: Using headless=False is often required for bot protection (like Akamai on Abercrombie)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
        )
        page = await context.new_page()
        
        # Inject stealth properties to avoid WebDriver detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        for store_config in stores_to_scrape:
            scraper = get_scraper_for_store(store_config.name)
            products = await scraper.scrape(page, store_config.url)
            all_products.extend(products)

        await browser.close()

    return all_products


def main():
    parser = argparse.ArgumentParser(description="Multi-Store Product Scraper")
    parser.add_argument(
        "category", 
        type=str, 
        help="The category path to scrape (e.g., 'Womens/Bottoms/Jeans')"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the results in JSON format"
    )

    args = parser.parse_args()
    
    products = asyncio.run(get_products_by_category(args.category))
    
    if not products:
        print("No products found or error occurred.")
        return

    if args.json:
        # Dump as JSON array
        print(json.dumps([asdict(p) for p in products], indent=2))
    else:
        print(f"\nFound {len(products)} total products:\n")
        print("-" * 80)
        for p in products:
            print(f"Store: {p.store:<15} | Price: {p.price:<10} | Name: {p.item_name}")
            print(f"Link : {p.item_link}")
            print(f"Image: {p.item_image_link}")
            print("-" * 80)


if __name__ == "__main__":
    main()
