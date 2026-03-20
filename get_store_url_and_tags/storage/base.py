"""Abstract storage interface. No assumptions about the underlying storage mechanism."""

from abc import ABC, abstractmethod
from datetime import datetime
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

    def delete_items_not_updated_since(
        self, cutoff_utc: datetime, store_names: list[str] | None = None
    ) -> int:
        """Remove items last updated before ``cutoff_utc``; optional ``store_names`` scopes the delete.

        Returns the number of rows removed. Backends that do not support cleanup should raise
        :class:`NotImplementedError`.
        """
        raise NotImplementedError(
            "delete_items_not_updated_since is not implemented for this storage backend"
        )
