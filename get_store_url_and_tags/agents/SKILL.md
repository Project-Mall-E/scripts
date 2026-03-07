---
name: Creating New Scraper Parsers
description: Instructions for using the HTML dump feature to create new content parsers in scrapers.py
---

# Creating New Scraper Parsers

This skill helps you create new website product parsers using the HTML dump feature. The system is designed to navigate to a clothing category URL, capture the raw HTML of the page, and parse clothing items into `Product` objects.

## Prerequisites
The main entry point for the scraping system allows for dumping the raw HTML of a website locally with the `--dump-item-html` flag. This functionality helps you inspect the DOM offline without dealing with slow load times or bot protections while developing a parser.

## Step 1: Dump the Target HTML
If the user requests a parser for a new store, first run the orchestrator with the debug flag targeting that store. You can limit the number of URLs using `--max-urls-per-shop 1` to speed up the process.

```bash
python main.py --stores <StoreName> --max-urls-per-shop 1 --dump-item-html
```

This will create a `debug/` directory containing a file named `<url>-dump.html`.

## Step 2: Analyze the HTML
Use your file viewing tools (e.g. `view_file` or `grep_search`) to inspect the dumped HTML file.
Look for the container that wraps individual products (often a `div` or `li` with a class like `product-card`, `product-tile`, etc.).

Take note of the selectors (classes, data attributes, etc.) for:
- Product Name
- Product Price (Sale Price vs. List Price)
- Product URL
- Product Image URL

## Step 3: Implement the Parser
Open `get_store_url_and_tags/scraping/scrapers.py`.

1. Create a new class that inherits from `BaseScraper`.
2. Implement the `__init__` method, defining the store name and base URL.
3. Implement the `parse_html` method. This method takes a BeautifulSoup object (`soup`) and a `tags` list.
4. Extract the products and append them as `Product` objects.

Example prototype:
```python
from bs4 import BeautifulSoup
from typing import List
from .base import BaseScraper
from .product import Product

class NewStoreScraper(BaseScraper):
    def __init__(self):
        super().__init__("NewStore")
        self.base_url = "https://www.newstore.com"

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        products = []
        cards = soup.find_all("div", class_="product-card-class")
        
        for card in cards:
            # Extract name, price, link, img
            products.append(Product(
                store=self.store_name,
                item_name=name,
                item_image_link=img,
                item_link=link,
                price=price,
                tags=tags
            ))
            
        return products
```

## Step 4: Register the Scraper
In `scrapers.py`, locate the `get_scraper_for_store` factory function. Add an `elif` block to return your new scraper when requested:

```python
def get_scraper_for_store(store_name: str) -> BaseScraper:
    # ... existing stores ...
    elif store_name == "NewStore":
        return NewStoreScraper()
    return None
```

## Step 5: Verify the Scraper
Run the orchestrator again targeting the specific store to verify the newly parsed output correctly prints to the terminal:

```bash
python main.py --stores <StoreName> --max-urls-per-shop 1
```
Check the terminal output to ensure that the item name, price, link, and image are properly populated and not `None`.
