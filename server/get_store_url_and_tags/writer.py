from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Tuple
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'get_clothing_items')))

from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StoreConfigEntry:
    """Represents a single entry for store_config.py."""
    name: str
    url: str
    tags: List[str]
    
    def __hash__(self):
        return hash((self.name, self.url))
    
    def __eq__(self, other):
        if isinstance(other, StoreConfigEntry):
            return self.name == other.name and self.url == other.url
        return False


class StoreConfigWriter:
    """
    Writes discovered URLs and tags to store_config.py.
    
    Handles merging with existing entries and deduplication.
    """
    
    def __init__(self, output_path: str = None):
        if output_path is None:
            output_path = Path(__file__).parent.parent / "get_clothing_items" / "store_config.py"
        self.output_path = Path(output_path)
    
    def _load_existing_entries(self) -> List[StoreConfigEntry]:
        """Load existing entries from store_config.py."""
        if not self.output_path.exists():
            return []
        
        entries = []
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("store_config", self.output_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "STORE_CONFIG"):
                for config in module.STORE_CONFIG:
                    entries.append(StoreConfigEntry(
                        name=config.name,
                        url=config.url,
                        tags=list(config.tags)
                    ))
            
            logger.info(f"Loaded {len(entries)} existing entries from {self.output_path}")
        except Exception as e:
            logger.warning(f"Could not load existing config: {e}")
        
        return entries
    
    def _merge_entries(
        self,
        existing: List[StoreConfigEntry],
        new: List[StoreConfigEntry]
    ) -> List[StoreConfigEntry]:
        """
        Merge existing entries with new ones.
        
        Strategy:
        - Keep existing entries that aren't duplicated by new ones
        - Add all new entries
        - Deduplicate by (store, url)
        """
        seen: Set[Tuple[str, str]] = set()
        merged = []
        
        for entry in new:
            key = (entry.name, entry.url.rstrip("/"))
            if key not in seen:
                seen.add(key)
                merged.append(entry)
        
        for entry in existing:
            key = (entry.name, entry.url.rstrip("/"))
            if key not in seen:
                seen.add(key)
                merged.append(entry)
        
        merged.sort(key=lambda e: (e.name, e.tags, e.url))
        
        return merged
    
    def _format_entry(self, entry: StoreConfigEntry) -> str:
        """Format a single entry as Python code."""
        tags_str = repr(entry.tags)
        return f'    StoreConfig("{entry.name}", "{entry.url}", {tags_str}),'
    
    def write(
        self,
        entries: List[StoreConfigEntry],
        merge_existing: bool = True
    ) -> int:
        """
        Write entries to store_config.py.
        
        Args:
            entries: List of entries to write
            merge_existing: Whether to merge with existing entries
            
        Returns:
            Number of entries written
        """
        if merge_existing:
            existing = self._load_existing_entries()
            entries = self._merge_entries(existing, entries)
        
        lines = [
            "from dataclasses import dataclass",
            "from typing import List",
            "",
            "",
            "@dataclass",
            "class StoreConfig:",
            '    """Configuration for a store category URL."""',
            "    name: str",
            "    url: str",
            "    tags: List[str]",
            "",
            "",
            "STORE_CONFIG = [",
        ]
        
        for entry in entries:
            lines.append(self._format_entry(entry))
        
        lines.append("]")
        lines.append("")
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, "w") as f:
            f.write("\n".join(lines))
        
        logger.info(f"Wrote {len(entries)} entries to {self.output_path}")
        return len(entries)
