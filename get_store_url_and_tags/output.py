"""Emit results and debug dumps. Keeps I/O and formatting out of pipeline and main."""

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import List

from .models import Product, StoreLink
from .utils.logger import get_logger

logger = get_logger(__name__)


def dump_discovered_urls(entries: List[StoreLink], debug_dir: Path) -> None:
    """Write discovered StoreLinks to debug/{store}_urls_{timestamp}.json per store."""
    if not entries:
        return

    debug_dir = Path(debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)

    by_store: dict = {}
    for entry in entries:
        if entry.name not in by_store:
            by_store[entry.name] = []
        by_store[entry.name].append(asdict(entry))

    for store_name, store_urls in by_store.items():
        timestamp = int(time.time())
        safe_name = store_name.lower().replace(" ", "_")
        debug_file = debug_dir / f"{safe_name}_urls_{timestamp}.json"
        with open(debug_file, "w") as f:
            json.dump(store_urls, f, indent=2)
        logger.info("Dumped %d URLs for %s to %s", len(store_urls), store_name, debug_file)


def emit_products(
    products: List[Product],
    *,
    format: str = "text",
) -> None:
    """
    Print products to stdout.
    format: "json" -> JSON array; "text" -> human-readable lines.
    """
    if not products:
        return

    if format == "json":
        print(json.dumps([asdict(p) for p in products], indent=2))
    else:
        print(f"\nFound {len(products)} total products:\n")
        print("-" * 80)
        for p in products:
            print(f"Store: {p.store:<15} | Price: {p.price:<10} | Name: {p.item_name}")
            print(f"Link : {p.item_link}")
            print(f"Image: {p.item_image_link}")
            print(f"Tags : {p.tags}")
            print("-" * 80)


def emit_discovery_summary(entries: List[StoreLink]) -> None:
    """Log a short summary of discovery results (stores and tag count)."""
    if not entries:
        return
    stores_found = set(e.name for e in entries)
    logger.info("Discovery complete!")
    logger.info("  Total URLs matching criteria: %d", len(entries))
    logger.info("  Stores: %s", ", ".join(sorted(stores_found)))
    all_tags = set()
    for e in entries:
        all_tags.update(e.tags)
    logger.info("  Unique tags: %d", len(all_tags))
