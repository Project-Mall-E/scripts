"""High-level pipeline: discovery -> optional scraping -> optional storage. Used by main."""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from .config import Config, load_config
from .models import Product, StoreLink
from .orchestrator import DiscoveryOrchestrator
from .output import dump_discovered_urls, emit_discovery_summary, emit_products
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineOptions:
    """
    Options for run_pipeline (filled from CLI or callers).
    See README.md for full config docs; main.py parse_args() maps CLI here.
    """
    stores_filter: Optional[List[str]] = None  # None = all stores
    headless: bool = True
    dump_urls: bool = False  # --dump-store-urls: write discovered URLs to debug/
    disable_fetch_clothing_items: bool = False  # discovery only, no scraping
    sequential: bool = False  # --sequential: run discovery and scraping one store at a time
    category: Optional[str] = None  # e.g. "Womens/Bottoms/Jeans"; skip discovery, scrape only this
    output_json: bool = False
    dump_item_html: bool = False  # save listing page HTML to debug/ for parser development
    max_urls_per_shop: Optional[int] = None  # cap URLs per store (verification/debug)
    store_in_database: bool = False
    delete_stale_items_days: Optional[int] = None  # if set, delete products older than this many days
    debug_dir: Optional[Path] = None  # where to write dump_store_urls / dump_item_html


@dataclass
class PipelineResult:
    """Result of run_pipeline."""
    entries: List[StoreLink] = field(default_factory=list)
    products: Optional[List[Product]] = None

    @property
    def success(self) -> bool:
        return True  # Caller uses exceptions for failure


async def run_pipeline(
    config: Config,
    options: PipelineOptions,
) -> PipelineResult:
    """
    Run discovery, optional category filter, optional dump, optional scraping, optional storage.
    Returns PipelineResult(entries, products). Does not emit to stdout; caller calls output.emit_*.
    """
    if options.debug_dir is None:
        options.debug_dir = Path(__file__).resolve().parent / "debug"

    logger.info("Discovery phase starting ...")
    orchestrator = DiscoveryOrchestrator(config=config, headless=options.headless)
    try:
        entries = await orchestrator.run(stores=options.stores_filter, sequential=options.sequential)
    finally:
        await orchestrator.close()
    logger.info("Discovery phase complete: %d entries", len(entries))

    if options.category:
        category_tags = options.category.split("/")
        entries = [e for e in entries if e.tags == category_tags]
        if not entries:
            raise ValueError(
                f"Category '{options.category}' not found or filtered out after discovery."
            )
        logger.info(
            "Filtered down to %d matching entries for category '%s'.",
            len(entries),
            options.category,
        )

    emit_discovery_summary(entries)

    if options.dump_urls and entries:
        dump_discovered_urls(entries, options.debug_dir)

    products: Optional[List[Product]] = None
    if entries and not options.disable_fetch_clothing_items:
        from .scraping.orchestrator import ScrapingOrchestrator

        logger.info(
            "Scraping phase starting (%s) ...",
            "sequential (one store at a time)" if options.sequential else "parallel per store",
        )
        scraping_orchestrator = ScrapingOrchestrator(
            headless=options.headless,
            dump_item_html=options.dump_item_html,
            settings=config.settings,
        )
        products = await scraping_orchestrator.run(
            entries,
            max_urls_per_shop=options.max_urls_per_shop,
            sequential=options.sequential,
        )

        if options.store_in_database and products:
            provider = _get_storage_provider()
            for p in products:
                try:
                    provider.upsert(p)
                except Exception as e:
                    logger.error("Failed to persist product %s: %s", p.item_link, e)

    if options.delete_stale_items_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=options.delete_stale_items_days)
        provider = _get_storage_provider()
        store_scope = options.stores_filter
        try:
            removed = provider.delete_items_not_updated_since(cutoff, store_names=store_scope)
        except NotImplementedError as e:
            logger.error(
                "Stale product delete is not supported for this storage backend (%s)", e
            )
        except Exception as e:
            logger.error("Stale product delete failed: %s", e, exc_info=True)
        else:
            scope_msg = (
                f"stores {store_scope!r}" if store_scope else "all stores"
            )
            logger.info(
                "Stale product delete: removed %d row(s) (%s; updated_at before %s)",
                removed,
                scope_msg,
                cutoff.isoformat(),
            )

    return PipelineResult(entries=entries, products=products)


def _get_storage_provider():
    """Return the configured storage provider (Supabase or Firestore).

    Default is Supabase unless `STORAGE_BACKEND=firestore`.
    Used for `--store-in-database` upserts and for `--delete-stale-items` when configured.
    """
    from .storage import FirestoreStorageProvider, SupabaseStorageProvider
    backend = os.environ.get("STORAGE_BACKEND", "").strip().lower()
    if backend == "firestore":
        return FirestoreStorageProvider()
    # Default to Supabase. Note: SupabaseStorageProvider will validate SUPABASE_URL /
    # SUPABASE_SERVICE_ROLE_KEY when first used (e.g. `upsert()`).
    return SupabaseStorageProvider(
        url=os.environ.get("SUPABASE_URL"),
        key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    )
