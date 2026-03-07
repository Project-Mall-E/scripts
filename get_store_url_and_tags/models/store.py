"""Store configuration model."""

from dataclasses import dataclass, field
from typing import List, Optional


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
