"""Configuration loading. Depends only on models."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..models import StoreDefinition


@dataclass
class Settings:
    """Global settings for the discovery system (from config JSON "settings" block)."""
    rate_limit_seconds: float = 1.2  # delay between requests per domain (polite crawler default)
    rate_limit_jitter: float = 0.0  # optional ± seconds added to rate limit (e.g. 0.2 for ±0.2s)
    max_retries: int = 3
    request_timeout_seconds: float = 30.0
    max_crawl_depth: int = 2  # link crawler max depth
    # Scraping (product listing pages)
    scrape_page_wait_seconds: float = 2.5  # wait after page load before scraping
    scrape_scroll_delay_seconds: float = 0.6  # delay between scroll steps
    scrape_scroll_count: int = 2  # number of scroll steps to mimic human behavior
    # Navigation discovery
    navigation_wait_seconds: float = 1.5  # wait after goto before extracting nav
    navigation_hover_delay_seconds: float = 0.2  # delay per hover
    navigation_post_hover_seconds: float = 0.5  # delay after hover block before extracting links
    # Link crawler
    link_crawler_post_goto_seconds: float = 0.5  # wait after each page.goto (rate_limiter handles main delay)


@dataclass
class Config:
    """Configuration container: list of stores + global settings. See README §2."""
    stores: List[StoreDefinition]
    settings: Settings


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config file, or None to use default

    Returns:
        Loaded Config object
    """
    if config_path is None:
        config_path = Path(__file__).parent / "stores.json"
    else:
        config_path = Path(config_path)

    with open(config_path, "r") as f:
        data = json.load(f)

    stores = [
        StoreDefinition(
            name=s["name"],
            homepage=s["homepage"],
            domain=s["domain"],
            discovery_strategy=s.get("discovery_strategy", "auto"),
            extra_category_patterns=s.get("extra_category_patterns", []),
            extra_exclude_patterns=s.get("extra_exclude_patterns", []),
            max_path_depth=s.get("max_path_depth", None),
        )
        for s in data.get("stores", [])
    ]

    settings_data = data.get("settings", {})
    settings = Settings(
        rate_limit_seconds=settings_data.get("rate_limit_seconds", 1.2),
        rate_limit_jitter=settings_data.get("rate_limit_jitter", 0.0),
        max_retries=settings_data.get("max_retries", 3),
        request_timeout_seconds=settings_data.get("request_timeout_seconds", 30.0),
        max_crawl_depth=settings_data.get("max_crawl_depth", 2),
        scrape_page_wait_seconds=settings_data.get("scrape_page_wait_seconds", 2.5),
        scrape_scroll_delay_seconds=settings_data.get("scrape_scroll_delay_seconds", 0.6),
        scrape_scroll_count=settings_data.get("scrape_scroll_count", 2),
        navigation_wait_seconds=settings_data.get("navigation_wait_seconds", 1.5),
        navigation_hover_delay_seconds=settings_data.get("navigation_hover_delay_seconds", 0.2),
        navigation_post_hover_seconds=settings_data.get("navigation_post_hover_seconds", 0.5),
        link_crawler_post_goto_seconds=settings_data.get("link_crawler_post_goto_seconds", 0.5),
    )

    return Config(stores=stores, settings=settings)


def save_config(config: Config, config_path: str) -> None:
    """
    Save configuration to JSON file.

    Args:
        config: Config object to save
        config_path: Path to save to
    """
    data = {
        "stores": [
            {
                "name": s.name,
                "homepage": s.homepage,
                "domain": s.domain,
                "discovery_strategy": s.discovery_strategy,
            }
            for s in config.stores
        ],
        "settings": {
            "rate_limit_seconds": config.settings.rate_limit_seconds,
            "rate_limit_jitter": config.settings.rate_limit_jitter,
            "max_retries": config.settings.max_retries,
            "request_timeout_seconds": config.settings.request_timeout_seconds,
            "max_crawl_depth": config.settings.max_crawl_depth,
            "scrape_page_wait_seconds": config.settings.scrape_page_wait_seconds,
            "scrape_scroll_delay_seconds": config.settings.scrape_scroll_delay_seconds,
            "scrape_scroll_count": config.settings.scrape_scroll_count,
            "navigation_wait_seconds": config.settings.navigation_wait_seconds,
            "navigation_hover_delay_seconds": config.settings.navigation_hover_delay_seconds,
            "navigation_post_hover_seconds": config.settings.navigation_post_hover_seconds,
            "link_crawler_post_goto_seconds": config.settings.link_crawler_post_goto_seconds,
        }
    }

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
