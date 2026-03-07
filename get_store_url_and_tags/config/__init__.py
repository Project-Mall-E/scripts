import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..discovery.base import StoreDefinition


@dataclass
class Settings:
    """Global settings for the discovery system."""
    rate_limit_seconds: float = 2.0
    max_retries: int = 3
    request_timeout_seconds: float = 30.0
    max_crawl_depth: int = 2


@dataclass
class Config:
    """Configuration container for the discovery system."""
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
        rate_limit_seconds=settings_data.get("rate_limit_seconds", 2.0),
        max_retries=settings_data.get("max_retries", 3),
        request_timeout_seconds=settings_data.get("request_timeout_seconds", 30.0),
        max_crawl_depth=settings_data.get("max_crawl_depth", 2),
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
            "max_retries": config.settings.max_retries,
            "request_timeout_seconds": config.settings.request_timeout_seconds,
            "max_crawl_depth": config.settings.max_crawl_depth,
        }
    }
    
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
