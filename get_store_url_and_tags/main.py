#!/usr/bin/env python3
"""
Store Category URL Discovery and Tagging System

Discovers category URLs from clothing store websites and auto-generates
tags for use by the clothing item scraper.

Usage:
    python main.py                      # Process all stores
    python main.py --stores Abercrombie # Process specific store
    python main.py --dry-run            # Preview without writing
    python main.py --headless=false     # Show browser (for debugging)
"""

import argparse
import asyncio
import sys
from pathlib import Path

# When run as script (python main.py), ensure package is on path for imports
_server_dir = Path(__file__).resolve().parent.parent
if _server_dir not in [Path(p).resolve() for p in sys.path]:
    sys.path.insert(0, str(_server_dir))

from get_store_url_and_tags.config import load_config
from get_store_url_and_tags.orchestrator import DiscoveryOrchestrator
from get_store_url_and_tags.utils.logger import setup_logging, get_logger

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
    %(prog)s --dump-store-urls         Dump discovered URLs to debug/
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


async def main() -> int:
    args = parse_args()
    
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    logger.info("=" * 60)
    logger.info("Store Category URL Discovery System")
    logger.info("=" * 60)
    
    try:
        config = load_config(args.config)
        logger.info(f"Loaded {len(config.stores)} stores from config")
    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return 1
    
    stores_filter = None
    if args.stores:
        stores_filter = [s.strip() for s in args.stores.split(",")]
        logger.info(f"Filtering to stores: {stores_filter}")
    
    headless = args.headless.lower() == "true"
    
    orchestrator = DiscoveryOrchestrator(
        config=config,
        headless=headless
    )
    
    try:
        entries = await orchestrator.run(
            stores=stores_filter,
            dump_urls=args.dump_store_urls
        )
        
        if args.category:
            category_tags = args.category.split("/")
            entries = [e for e in entries if e.tags == category_tags]
            
            if not entries:
                logger.error(f"Category '{args.category}' not found or filtered out after discovery.")
                return 1
            
            logger.info(f"Filtered down to {len(entries)} matching entries for category '{args.category}'.")
        
        logger.info("=" * 60)
        logger.info(f"Discovery complete!")
        logger.info(f"  Total URLs matching criteria: {len(entries)}")
        
        if entries:
            stores_found = set(e.name for e in entries)
            logger.info(f"  Stores: {', '.join(sorted(stores_found))}")
            
            all_tags = set()
            for e in entries:
                all_tags.update(e.tags)
            logger.info(f"  Unique tags: {len(all_tags)}")
            
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        return 1
    finally:
        await orchestrator.close()

    if entries and not args.disable_fetch_clothing_items:
        from get_store_url_and_tags.scraping.orchestrator import ScrapingOrchestrator
        import json
        from dataclasses import asdict
        
        logger.info("=" * 60)
        logger.info("Starting Product Scraping")
        logger.info("=" * 60)
        
        try:
            scraping_orchestrator = ScrapingOrchestrator(headless=headless, dump_item_html=args.dump_item_html)
            products = await scraping_orchestrator.run(entries, max_urls_per_shop=args.max_urls_per_shop)

            if args.store_in_database and products:
                from get_store_url_and_tags.storage import FirestoreStorageProvider
                provider = FirestoreStorageProvider()
                for p in products:
                    try:
                        provider.upsert(p)
                    except Exception as e:
                        logger.error("Failed to persist product %s: %s", p.item_link, e)

            if not products:
                logger.info("No products found.")
            elif args.json:
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
        except Exception as e:
            logger.error(f"Scraping failed: {e}", exc_info=True)
            return 1
            
    logger.info("=" * 60)
    return 0


def run():
    """Entry point for the CLI."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
