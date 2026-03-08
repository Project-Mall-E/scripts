"""Tests for utils.logger."""

import logging
from pathlib import Path

import pytest

from get_store_url_and_tags.utils.logger import get_logger, setup_logging


def test_get_logger() -> None:
    logger = get_logger("test.name")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.name"


def test_setup_logging_with_file(tmp_path: Path) -> None:
    log_file = str(tmp_path / "test.log")
    setup_logging(log_file=log_file, level=logging.DEBUG, include_console=False)
    logger = get_logger("test_setup")
    logger.info("hello")
    assert Path(log_file).exists()
    assert "hello" in Path(log_file).read_text()


def test_setup_logging_include_console() -> None:
    setup_logging(log_file=None, level=logging.INFO, include_console=True)
    logger = get_logger("test_console")
    logger.info("console test")
    # No exception; console handler is added
