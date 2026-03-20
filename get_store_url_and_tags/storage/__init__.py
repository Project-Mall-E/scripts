"""Storage backends for persisting scraped products. Use FirestoreStorageProvider or SupabaseStorageProvider."""

from .base import StorageProvider
from .firestore_provider import FirestoreStorageProvider
from .supabase_provider import SupabaseStorageProvider

__all__ = [
    "StorageProvider",
    "FirestoreStorageProvider",
    "SupabaseStorageProvider",
]
