#!/usr/bin/env python3
"""
Store Category URL Discovery and Tagging System

Discovers category URLs from clothing store websites and auto-generates
tags for use by the clothing item scraper. Optionally scrapes product
listings from those URLs using per-store parsers (scrapers).

Usage (run from repo root so scripts/ is on PYTHONPATH):
    PYTHONPATH=scripts python -m get_store_url_and_tags
    PYTHONPATH=scripts python -m get_store_url_and_tags --stores Abercrombie
    PYTHONPATH=scripts python -m get_store_url_and_tags --disable-fetch-clothing-items  # discovery only
    PYTHONPATH=scripts python -m get_store_url_and_tags --headless=false
    PYTHONPATH=scripts python -m get_store_url_and_tags --dump-store-urls --max-urls-per-shop 2  # verify stores

See README.md for full docs: config options, adding stores, scrapers (parsers), and debug options.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# When run as script (python main.py), ensure package parent is on path
if __name__ == "__main__":
    _script_dir = Path(__file__).resolve().parent
    _parent = _script_dir.parent
    if _parent not in [Path(p).resolve() for p in sys.path]:
        sys.path.insert(0, str(_parent))

# Load .env into os.environ so STORAGE_BACKEND, SUPABASE_*, etc. work from a .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from get_store_url_and_tags.app import PipelineOptions, run_pipeline
from get_store_url_and_tags.config import load_config
from get_store_url_and_tags.output import emit_products
from get_store_url_and_tags.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def _positive_int(value: str) -> int:
    try:
        v = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from exc
    if v <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return v


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover and tag category URLs from clothing stores",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                           Process all configured stores
    %(prog)s --stores Abercrombie      Process only Abercrombie
    %(prog)s --stores "A,B"            Process stores A and B
    %(prog)s --dump-store-urls         Dump discovered store URLs to debug/
    %(prog)s --config ./my-stores.json Use custom config file
    %(prog)s --sequential               Run one store at a time (no parallel)
        """
    )

    # --- Store selection and config ---
    parser.add_argument(
        "--stores",
        type=str,
        default=None,
        help="Comma-separated list of store names to process (default: all)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to stores.json config file (default: config/stores.json)"
    )

    # --- Debug / verification (see README §5) ---
    parser.add_argument(
        "--dump-store-urls",
        action="store_true",
        help="Dump discovered category URLs to debug/<store>_urls_<timestamp>.json"
    )
    parser.add_argument(
        "--max-urls-per-shop",
        type=int,
        default=None,
        help="Cap category URLs scraped per store (for quick verification; e.g. 2)"
    )
    parser.add_argument(
        "--dump-item-html",
        action="store_true",
        help="Save product listing HTML to debug/<safe_url>-dump.html for writing new parsers"
    )

    # --- Browser and pipeline ---
    parser.add_argument(
        "--headless",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Run browser headless (default: true); use false if site has bot checks"
    )
    parser.add_argument(
        "--disable-fetch-clothing-items",
        action="store_true",
        help="Run discovery only; do not scrape product listings"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run discovery and scraping one store at a time (no parallel stores)"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Skip discovery; only fetch items for this category path (e.g. Womens/Bottoms/Jeans)"
    )

    # --- Output ---
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit scraped products as JSON to stdout"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging"
    )
    parser.add_argument(
        "--store-in-database",
        action="store_true",
        help="Persist scraped products to storage backend (default: Supabase)"
    )
    parser.add_argument(
        "--delete-stale-items",
        type=_positive_int,
        metavar="DAYS",
        default=None,
        dest="delete_stale_items",
        help=(
            "After the run, delete catalog rows with updated_at older than DAYS days "
            "(Supabase: products table). Use with --stores to limit to those store names."
        ),
    )

    return parser.parse_args()


def args_to_options(args: argparse.Namespace) -> PipelineOptions:
    """Build PipelineOptions from parsed CLI args."""
    stores_filter = None
    if args.stores:
        stores_filter = [s.strip() for s in args.stores.split(",")]

    return PipelineOptions(
        stores_filter=stores_filter,
        headless=args.headless.lower() == "true",
        dump_urls=args.dump_store_urls,
        disable_fetch_clothing_items=args.disable_fetch_clothing_items,
        sequential=args.sequential,
        category=args.category,
        output_json=args.json,
        dump_item_html=args.dump_item_html,
        max_urls_per_shop=args.max_urls_per_shop,
        store_in_database=args.store_in_database,
        delete_stale_items_days=args.delete_stale_items,
        debug_dir=Path(__file__).resolve().parent / "debug",
    )


async def main() -> int:
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)

    logger.info("=" * 60)
    logger.info("Store Category URL Discovery System")
    logger.info("=" * 60)

    try:
        config = load_config(args.config)
        logger.info("Loaded %d stores from config", len(config.stores))
    except FileNotFoundError as e:
        logger.error("Config file not found: %s", e)
        return 1
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        return 1

    if args.stores:
        logger.info("Filtering to stores: %s", [s.strip() for s in args.stores.split(",")])

    if args.delete_stale_items is None:
        raw = os.environ.get("DELETE_STALE_ITEMS_DAYS", "").strip()
        if raw:
            try:
                v = int(raw)
                if v <= 0:
                    raise ValueError()
                args.delete_stale_items = v
            except ValueError:
                logger.error(
                    "DELETE_STALE_ITEMS_DAYS must be a positive integer, got %r",
                    raw,
                )
                return 1

    options = args_to_options(args)

    try:
        result = await run_pipeline(config, options)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except ValueError as e:
        logger.error("%s", e)
        return 1
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        return 1

    if result.products is not None:
        if not result.products:
            logger.info("No products found.")
        else:
            emit_products(
                result.products,
                format="json" if options.output_json else "text",
            )

    logger.info("=" * 60)
    return 0


def run() -> None:
    """Entry point for the CLI."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
