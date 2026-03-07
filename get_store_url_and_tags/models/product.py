"""Scraped product model."""

from dataclasses import dataclass


@dataclass
class Product:
    """A scraped clothing item."""

    store: str
    item_name: str
    item_image_link: str
    item_link: str
    price: str
    tags: list
