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
    %(prog)s --dry-run                 Preview results without writing
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
        "--dry-run",
        action="store_true",
        help="Preview discovered URLs without writing to store_config.py"
    )
    
    parser.add_argument(
        "--headless",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Run browser in headless mode (default: true)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
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
            dry_run=args.dry_run
        )
        
        logger.info("=" * 60)
        logger.info(f"Discovery complete!")
        logger.info(f"  Total URLs discovered: {len(entries)}")
        
        if entries:
            stores_found = set(e.name for e in entries)
            logger.info(f"  Stores: {', '.join(sorted(stores_found))}")
            
            all_tags = set()
            for e in entries:
                all_tags.update(e.tags)
            logger.info(f"  Unique tags: {len(all_tags)}")
        
        if args.dry_run:
            logger.info("  (Dry run - no files modified)")
        else:
            output_path = Path(__file__).parent.parent / "get_clothing_items" / "store_config.py"
            logger.info(f"  Output: {output_path}")
        
        logger.info("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        return 1
    finally:
        await orchestrator.close()


def run():
    """Entry point for the CLI."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
