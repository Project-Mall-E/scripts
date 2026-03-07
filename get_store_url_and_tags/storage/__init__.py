"""Storage backends for persisting scraped products. Use FirestoreStorageProvider for Firestore."""

from .base import StorageProvider
from .firestore_provider import FirestoreStorageProvider

__all__ = [
    "StorageProvider",
    "FirestoreStorageProvider",
]
