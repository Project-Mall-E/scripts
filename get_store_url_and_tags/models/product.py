"""Scraped product model."""

from dataclasses import dataclass, field


@dataclass
class Product:
    """
    A scraped clothing item.

    item_descriptions holds unique lowercase words tokenized from listing-card
    facet text (e.g. color, fit, fabric), distinct from category tags.
    """

    store: str
    item_name: str
    item_image_links: list[str]
    item_link: str
    price: str
    tags: list
    item_descriptions: list[str] = field(default_factory=list)
