"""Shared helpers for storage providers."""

from dataclasses import asdict, is_dataclass
from typing import Any


def item_to_dict(item: Any) -> dict[str, Any]:
    """Convert a Product-like item to a plain dict for persistence."""
    if is_dataclass(item) and not isinstance(item, type):
        return asdict(item)
    if isinstance(item, dict):
        return dict(item)
    raise TypeError("item must be a dataclass instance or dict")
