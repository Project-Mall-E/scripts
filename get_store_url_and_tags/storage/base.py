"""Abstract storage interface. No assumptions about the underlying storage mechanism."""

from abc import ABC, abstractmethod
from typing import Any


class StorageProvider(ABC):
    """Abstract base class for persisting and retrieving items by URL."""

    @abstractmethod
    def upsert(self, item: Any) -> None:
        """Insert or update a single item."""
        ...

    @abstractmethod
    def get_by_url(self, url: str) -> Any | None:
        """Return the stored item for the given URL, or None if not found."""
        ...
