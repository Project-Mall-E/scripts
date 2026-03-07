from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


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


@dataclass
class StoreDefinition:
    """Configuration for a store to crawl."""
    
    name: str
    homepage: str
    domain: str
    discovery_strategy: str = "auto"
    extra_category_patterns: List[str] = field(default_factory=list)
    extra_exclude_patterns: List[str] = field(default_factory=list)
    max_path_depth: Optional[int] = None


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
