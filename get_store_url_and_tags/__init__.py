"""
Store Category URL Discovery and Tagging System

This package discovers category URLs from clothing store websites
and auto-generates tags for use by the clothing item scraper.
"""

from .orchestrator import DiscoveryOrchestrator
from .config import load_config, Config
from .writer import StoreConfigWriter, StoreConfigEntry

__all__ = [
    "DiscoveryOrchestrator",
    "load_config",
    "Config",
    "StoreConfigWriter",
    "StoreConfigEntry",
]

__version__ = "1.0.0"
