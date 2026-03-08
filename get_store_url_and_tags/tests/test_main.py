"""Tests for main."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from get_store_url_and_tags.main import args_to_options, parse_args


def test_parse_args_defaults() -> None:
    with patch.object(sys, "argv", ["get_store_url_and_tags"]):
        args = parse_args()
    assert args.stores is None
    assert args.config is None
    assert args.headless == "true"
    assert args.sequential is False
    assert args.json is False


def test_parse_args_stores_and_config() -> None:
    with patch.object(sys, "argv", [
        "get_store_url_and_tags",
        "--stores", "Abercrombie,AmericanEagle",
        "--config", "/path/to/stores.json",
    ]):
        args = parse_args()
    assert args.stores == "Abercrombie,AmericanEagle"
    assert args.config == "/path/to/stores.json"


def test_parse_args_headless_false() -> None:
    with patch.object(sys, "argv", ["get_store_url_and_tags", "--headless", "false"]):
        args = parse_args()
    assert args.headless == "false"


def test_parse_args_sequential_and_dump() -> None:
    with patch.object(sys, "argv", [
        "get_store_url_and_tags",
        "--sequential",
        "--dump-store-urls",
        "--disable-fetch-clothing-items",
    ]):
        args = parse_args()
    assert args.sequential is True
    assert args.dump_store_urls is True
    assert args.disable_fetch_clothing_items is True


def test_args_to_options_defaults() -> None:
    with patch.object(sys, "argv", ["get_store_url_and_tags"]):
        args = parse_args()
    opts = args_to_options(args)
    assert opts.stores_filter is None
    assert opts.headless is True
    assert opts.dump_urls is False
    assert opts.sequential is False


def test_args_to_options_stores_filter() -> None:
    with patch.object(sys, "argv", ["get_store_url_and_tags", "--stores", "A, B"]):
        args = parse_args()
    opts = args_to_options(args)
    assert opts.stores_filter == ["A", "B"]


def test_args_to_options_headless_false() -> None:
    with patch.object(sys, "argv", ["get_store_url_and_tags", "--headless", "false"]):
        args = parse_args()
    opts = args_to_options(args)
    assert opts.headless is False


@pytest.mark.asyncio
async def test_main_success() -> None:
    from get_store_url_and_tags.main import main
    with patch.object(sys, "argv", ["get_store_url_and_tags", "--stores", "X"]):
        with patch("get_store_url_and_tags.main.load_config") as mock_load:
            from get_store_url_and_tags.config import Config
            from get_store_url_and_tags.models.store import StoreDefinition
            from get_store_url_and_tags.config import Settings
            mock_load.return_value = Config(stores=[StoreDefinition(name="X", homepage="https://x.com", domain="x.com")], settings=Settings())
            async def run_mock(c, o):
                from get_store_url_and_tags.app import PipelineResult
                return PipelineResult(entries=[], products=None)
            with patch("get_store_url_and_tags.main.run_pipeline", side_effect=run_mock):
                with patch("get_store_url_and_tags.main.setup_logging"):
                    exit_code = await main()
    assert exit_code == 0


@pytest.mark.asyncio
async def test_main_config_not_found() -> None:
    from get_store_url_and_tags.main import main
    with patch.object(sys, "argv", ["get_store_url_and_tags"]):
        with patch("get_store_url_and_tags.main.load_config", side_effect=FileNotFoundError("no file")):
            with patch("get_store_url_and_tags.main.setup_logging"):
                exit_code = await main()
    assert exit_code == 1


@pytest.mark.asyncio
async def test_main_value_error() -> None:
    from get_store_url_and_tags.main import main
    from get_store_url_and_tags.config import Config
    from get_store_url_and_tags.models.store import StoreDefinition
    from get_store_url_and_tags.config import Settings
    with patch.object(sys, "argv", ["get_store_url_and_tags"]):
        with patch("get_store_url_and_tags.main.load_config") as mock_load:
            mock_load.return_value = Config(
                stores=[StoreDefinition(name="X", homepage="https://x.com", domain="x.com")],
                settings=Settings(),
            )
            async def run_raise(c, o):
                raise ValueError("category not found")
            with patch("get_store_url_and_tags.main.run_pipeline", side_effect=run_raise):
                with patch("get_store_url_and_tags.main.setup_logging"):
                    exit_code = await main()
    assert exit_code == 1
