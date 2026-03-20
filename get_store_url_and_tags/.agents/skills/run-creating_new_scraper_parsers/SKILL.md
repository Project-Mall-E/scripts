---
name: run-creating_new_scraper_parsers 
description: Instructions for using the HTML dump feature to create new content parsers in the scrapers/ per-store structure. Includes virtualenv setup.
---

# Creating New Scraper Parsers

This skill helps you create new website product parsers using the HTML dump feature. The system navigates to a clothing category URL, captures the raw HTML, and parses items into `Product` objects.

## Prerequisites

### Virtualenv
Commands below assume the project virtualenv is activated. From the package root (`scripts/get_store_url_and_tags`):

```bash
cd scripts/get_store_url_and_tags
source .venv/bin/activate   # or: . venv/bin/activate
```

After activation, use `python main.py` (or `python -m get_store_url_and_tags` when run with `PYTHONPATH` set from repo root).

### Scraper layout (examples)
- `scraping/scrapers/american_eagle.py` → American Eagle
- `scraping/scrapers/abercrombie.py` → Abercrombie
- New store → add `scraping/scrapers/<store_slug>.py` and register it in `scraping/scrapers/__init__.py`

The main entry point supports dumping raw HTML with `--dump-item-html` so you can inspect the DOM offline while building a parser.

---

## Step 1: Dump the target HTML

Run the pipeline for the target store with HTML dump and a single URL per shop to speed things up:

```bash
# from scripts/get_store_url_and_tags with venv activated
python main.py --stores <StoreName> --max-urls-per-shop 1 --dump-item-html
```

This creates a `debug/` directory with files named `<url>-dump.html`.

---

## Step 2: Analyze the HTML

Inspect the dumped HTML (e.g. with your editor or grep). Find the container that wraps each product (often a `div` or `li` with a class like `product-card`, `product-tile`, etc.).

Note the selectors for:

- Product name  
- Price (sale vs list)  
- Product URL  
- Image URL(s)—listing cards may expose **multiple** `<img>` tags per product. Collect all usable absolute (or normalizable) URLs in **DOM order**, **dedupe** while preserving order, and pass them as `item_image_links: list[str]` (use `[]` when none).
- **Facet words** (color, fit, fabric, style hints on the card)—collect text from the card, then `collect_item_descriptions_from_card` yields **unique lowercase words** (first-seen order; use `[]` when none). Prefer stable `data-qa` / `data-testid` / `data-cmp` hooks; extend `scraping/card_descriptions.py` if the store needs new attribute patterns.

---

## Step 3: Implement the scraper

1. Define `STORE_NAME` (must match the store name in config, e.g. `"Loft"`).
2. Subclass `BaseScraper`, call `super().__init__(STORE_NAME)` and set `self.base_url`.
3. Implement `parse_html(self, soup, tags)` to find product cards and return a list of `Product` instances.

Example `scraping/scrapers/loft.py`:

```python
"""Loft product listing scraper."""

from typing import List
from bs4 import BeautifulSoup

from ..base import BaseScraper
from ..product import Product

STORE_NAME = "Loft"


class LoftScraper(BaseScraper):
    def __init__(self):
        super().__init__(STORE_NAME)
        self.base_url = "https://www.loft.com"

    def parse_html(self, soup: BeautifulSoup, tags: list[str]) -> List[Product]:
        products = []
        cards = soup.find_all("div", class_="product-card-class")  # use real selectors

        for card in cards:
            name = ...   # extract from card
            price = ...
            link = ...
            image_urls = [...]  # collect from card.find_all("img"), normalize, dedupe
            item_descriptions = [...]  # unique words: collect_item_descriptions_from_card(card, name)
            if link and link.startswith("/"):
                link = self.base_url + link
            products.append(Product(
                store=self.store_name,
                item_name=name,
                item_image_links=image_urls,
                item_link=link,
                price=price,
                tags=tags,
                item_descriptions=item_descriptions,
            ))
        return products
```

---

## Step 4: Register the scraper

In `scraping/scrapers/__init__.py`:

1. Import the new module.
2. Add an entry to `_REGISTRY` mapping `STORE_NAME` to the scraper class.

Example:

```python
from . import abercrombie
from . import american_eagle
from . import loft   # add this

_REGISTRY: dict[str, type[BaseScraper]] = {
    abercrombie.STORE_NAME: abercrombie.AbercrombieScraper,
    american_eagle.STORE_NAME: american_eagle.AmericanEagleScraper,
    loft.STORE_NAME: loft.LoftScraper,   # add this
}
```

`get_scraper_for_store(store_name)` will then return an instance for that store; no change needed elsewhere.

---

## Step 5: Verify

With venv activated, run the pipeline for the new store and check that parsed fields look correct:

```bash
python main.py --stores <StoreName> --max-urls-per-shop 1
```

Confirm in the output that item name, price, link, and at least one image URL are filled when the page provides imagery (or that `item_image_links` is empty only when the DOM has no usable images).

To see which stores have scrapers registered:

```python
from get_store_url_and_tags.scraping.scrapers import get_registered_store_names
print(get_registered_store_names())
```
