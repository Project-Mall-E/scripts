"""Discovery strategy abstraction. Data models live in models package."""

from abc import ABC, abstractmethod
from typing import List

from ..models import DiscoveredURL, StoreDefinition


# Re-export for backward compatibility
__all__ = ["DiscoveryStrategy", "DiscoveredURL", "StoreDefinition"]


class DiscoveryStrategy(ABC):
    """
    Abstract base class for URL discovery strategies.

    Each strategy implements a different method for finding category URLs:
    - Sitemap parsing
    - Navigation menu crawling
    - Link crawling with depth limit
    """

    name: str = "base"

    @abstractmethod
    async def discover(
        self,
        store: StoreDefinition,
        **kwargs
    ) -> List[DiscoveredURL]:
        """
        Discover category URLs for a store.

        Args:
            store: The store definition
            **kwargs: Strategy-specific options

        Returns:
            List of discovered URLs with metadata
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}>"
