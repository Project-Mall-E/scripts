"""
Store Category URL Discovery and Tagging System

This package discovers category URLs from clothing store websites
and auto-generates tags for use by the clothing item scraper.
"""

from .config import Config, load_config
from .models import DiscoveredURL, Product, StoreDefinition, StoreLink
from .orchestrator import DiscoveryOrchestrator

# Backward compat: StoreLink was previously from discovery.stores_links
__all__ = [
    "Config",
    "DiscoveredURL",
    "DiscoveryOrchestrator",
    "load_config",
    "Product",
    "StoreDefinition",
    "StoreLink",
]

__version__ = "1.0.0"
