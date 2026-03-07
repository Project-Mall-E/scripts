#!/usr/bin/env python3
"""
Store Category URL Discovery and Tagging System

Discovers category URLs from clothing store websites and auto-generates
tags for use by the clothing item scraper.

Usage (run from repo root so scripts/ is on PYTHONPATH, or install the package):
    PYTHONPATH=scripts python -m get_store_url_and_tags
    python -m get_store_url_and_tags --stores Abercrombie
    python -m get_store_url_and_tags --dry-run
    python -m get_store_url_and_tags --headless=false
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# When run as script (python main.py), ensure package parent is on path
if __name__ == "__main__":
    _script_dir = Path(__file__).resolve().parent
    _parent = _script_dir.parent
    if _parent not in [Path(p).resolve() for p in sys.path]:
        sys.path.insert(0, str(_parent))

from get_store_url_and_tags.app import PipelineOptions, run_pipeline
from get_store_url_and_tags.config import load_config
from get_store_url_and_tags.output import emit_products
from get_store_url_and_tags.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


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
        """
    )

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
        help="Path to stores.json config file (default: built-in)"
    )

    parser.add_argument(
        "--dump-store-urls",
        action="store_true",
        help="Dump discovered store URLs to the debug folder"
    )

    parser.add_argument(
        "--headless",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Run browser in headless mode (default: true)"
    )

    parser.add_argument(
        "--disable-fetch-clothing-items",
        action="store_true",
        help="Disable auto-fetching of clothing items after URL discovery"
    )

    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Skip discovery and only fetch clothing items for this category path (e.g., 'Womens/Bottoms/Jeans')"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output scraped products in JSON format"
    )

    parser.add_argument(
        "--dump-item-html",
        action="store_true",
        help="Dump product page HTML to debug/<safe_url>-dump.html for parser creation"
    )

    parser.add_argument(
        "--max-urls-per-shop",
        type=int,
        default=None,
        help="Maximum number of URLs to scrape per shop (for debugging)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--store-in-database",
        action="store_true",
        help="Persist scraped products to the configured storage backend (e.g. Firestore)"
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
        category=args.category,
        output_json=args.json,
        dump_item_html=args.dump_item_html,
        max_urls_per_shop=args.max_urls_per_shop,
        store_in_database=args.store_in_database,
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
