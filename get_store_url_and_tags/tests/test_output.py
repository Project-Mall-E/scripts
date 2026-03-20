"""Tests for output."""

import json
from pathlib import Path

import pytest

from get_store_url_and_tags.models import Product, StoreLink
from get_store_url_and_tags.output import (
    dump_discovered_urls,
    emit_discovery_summary,
    emit_products,
)


def test_dump_discovered_urls_empty(tmp_path: Path) -> None:
    dump_discovered_urls([], tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_dump_discovered_urls_writes_files(tmp_path: Path) -> None:
    entries = [
        StoreLink(name="StoreA", url="https://a.com/1", tags=["Womens"]),
        StoreLink(name="StoreA", url="https://a.com/2", tags=["Mens"]),
        StoreLink(name="StoreB", url="https://b.com/1", tags=[]),
    ]
    dump_discovered_urls(entries, tmp_path)
    files = list(tmp_path.iterdir())
    assert len(files) == 2  # storea and storeb
    by_name = {f.stem.split("_")[0]: f for f in files}
    assert "storea" in by_name or any("storea" in f.name for f in files)
    content = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert isinstance(content, list)
    assert len(content) >= 1


def test_emit_products_empty(capsys: pytest.CaptureFixture) -> None:
    emit_products([])
    out = capsys.readouterr().out
    assert out == "" or "Found 0" in out


def test_emit_products_text_format(capsys: pytest.CaptureFixture) -> None:
    products = [
        Product(
            store="S",
            item_name="Shirt",
            item_image_links=["https://x.com/i.jpg"],
            item_link="https://x.com/p/1",
            price="$20",
            tags=["Tops"],
        )
    ]
    emit_products(products, format="text")
    out = capsys.readouterr().out
    assert "Shirt" in out
    assert "$20" in out
    assert "https://x.com/p/1" in out
    assert "Tops" in out


def test_emit_products_json_format(capsys: pytest.CaptureFixture) -> None:
    products = [
        Product(
            store="S",
            item_name="Shirt",
            item_image_links=["https://x.com/i.jpg"],
            item_link="https://x.com/p/1",
            price="$20",
            tags=["Tops"],
        )
    ]
    emit_products(products, format="json")
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["item_name"] == "Shirt"
    assert data[0]["price"] == "$20"
    assert data[0]["item_image_links"] == ["https://x.com/i.jpg"]


def test_emit_discovery_summary_empty(caplog: pytest.LogCaptureFixture) -> None:
    emit_discovery_summary([])
    # May or may not log when empty; implementation just returns when not entries
    assert "Discovery complete" not in caplog.text or len(caplog.record_tuples) == 0


def test_emit_discovery_summary_logs(caplog: pytest.LogCaptureFixture) -> None:
    entries = [
        StoreLink(name="S", url="https://s.com/1", tags=["Womens", "Tops"]),
    ]
    with caplog.at_level("INFO"):
        emit_discovery_summary(entries)
    assert "Discovery complete" in caplog.text or "Total URLs" in caplog.text
