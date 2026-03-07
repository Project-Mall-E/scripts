"""Discovered URL model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DiscoveredURL:
    """Represents a discovered URL with associated metadata."""

    url: str
    store_name: str
    nav_text: Optional[str] = None
    page_title: Optional[str] = None
    breadcrumb_text: Optional[str] = None
    discovery_method: str = "unknown"
    depth: int = 0

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if isinstance(other, DiscoveredURL):
            return self.url == other.url
        return False
