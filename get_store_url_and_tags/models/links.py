"""Store link model (discovery output → scraping input)."""

from dataclasses import dataclass
from typing import List


@dataclass
class StoreLink:
    """A discovered category URL with normalized tags, ready for scraping."""

    name: str
    url: str
    tags: List[str]
