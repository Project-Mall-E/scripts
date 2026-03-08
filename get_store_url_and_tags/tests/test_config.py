"""Tests for config module."""

import json
from pathlib import Path

import pytest

from get_store_url_and_tags.config import Config, Settings, load_config, save_config
from get_store_url_and_tags.models import StoreDefinition


def test_settings_defaults() -> None:
    s = Settings()
    assert s.rate_limit_seconds == 1.2
    assert s.rate_limit_jitter == 0.0
    assert s.max_retries == 3
    assert s.request_timeout_seconds == 30.0
    assert s.max_crawl_depth == 2
    assert s.scrape_page_wait_seconds == 2.5
    assert s.navigation_wait_seconds == 1.5
    assert s.link_crawler_post_goto_seconds == 0.5


def test_settings_override() -> None:
    s = Settings(rate_limit_seconds=2.0, max_crawl_depth=3)
    assert s.rate_limit_seconds == 2.0
    assert s.max_crawl_depth == 3


def test_config_construction() -> None:
    store = StoreDefinition(name="S", homepage="https://s.com", domain="s.com")
    settings = Settings(rate_limit_seconds=1.0)
    config = Config(stores=[store], settings=settings)
    assert len(config.stores) == 1
    assert config.stores[0].name == "S"
    assert config.settings.rate_limit_seconds == 1.0


def test_load_config_explicit_path(sample_config_json: Path) -> None:
    config = load_config(str(sample_config_json))
    assert len(config.stores) == 1
    assert config.stores[0].name == "TestStore"
    assert config.stores[0].homepage == "https://www.teststore.com"
    assert config.stores[0].domain == "teststore.com"
    assert config.stores[0].discovery_strategy == "auto"
    assert config.settings.rate_limit_seconds == 1.5
    assert config.settings.rate_limit_jitter == 0.1


def test_load_config_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        load_config(str(missing))


def test_load_config_with_optional_store_fields(sample_config_json: Path) -> None:
    data = json.loads(sample_config_json.read_text())
    data["stores"][0]["extra_category_patterns"] = [r"/extra/"]
    data["stores"][0]["extra_exclude_patterns"] = [r"/exclude/"]
    data["stores"][0]["max_path_depth"] = 4
    sample_config_json.write_text(json.dumps(data))
    config = load_config(str(sample_config_json))
    assert config.stores[0].extra_category_patterns == [r"/extra/"]
    assert config.stores[0].extra_exclude_patterns == [r"/exclude/"]
    assert config.stores[0].max_path_depth == 4


def test_save_config_roundtrip(sample_config_json: Path, tmp_path: Path) -> None:
    config = load_config(str(sample_config_json))
    out_path = tmp_path / "out.json"
    save_config(config, str(out_path))
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert "stores" in data
    assert len(data["stores"]) == 1
    assert data["stores"][0]["name"] == "TestStore"
    assert data["stores"][0]["homepage"] == "https://www.teststore.com"
    assert "settings" in data
    assert data["settings"]["rate_limit_seconds"] == 1.5
