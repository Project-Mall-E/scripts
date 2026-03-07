"""
Store Category URL Discovery and Tagging System

This package discovers category URLs from clothing store websites
and auto-generates tags for use by the clothing item scraper.
"""

from .orchestrator import DiscoveryOrchestrator
from .config import load_config, Config
from .discovery.stores_links import StoreLink

__all__ = [
    "DiscoveryOrchestrator",
    "load_config",
    "Config",
    "StoreLink",
]

__version__ = "1.0.0"
