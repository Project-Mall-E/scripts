"""Supabase implementation of StorageProvider using RPC and products_with_tags view."""

import os
from datetime import datetime, timezone
from typing import Any

from .base import StorageProvider
from .common import item_to_dict


class SupabaseStorageProvider(StorageProvider):
    """Persist items via Supabase RPC upsert_product_from_json; read via products_with_tags view."""

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
    ) -> None:
        self._url = url or os.environ.get("SUPABASE_URL", "")
        self._key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self._client: Any = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        if not self._url or not self._key:
            raise ValueError(
                "Supabase storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "to be set (in environment or passed to the constructor)."
            )
        from supabase import create_client
        self._client = create_client(self._url, self._key)

    def upsert(self, item: Any) -> None:
        self._ensure_client()
        data = item_to_dict(item)
        url = data.get("item_link")
        if not url:
            raise ValueError("item must have an 'item_link' field")
        self._client.rpc("upsert_product_from_json", {"p": data}).execute()

    def get_by_url(self, url: str) -> dict | None:
        self._ensure_client()
        resp = (
            self._client.from_("products_with_tags")
            .select("*")
            .eq("item_link", url)
            .limit(1)
            .execute()
        )
        if not resp.data or len(resp.data) == 0:
            return None
        row = resp.data[0]
        return dict(row) if isinstance(row, dict) else row

    def delete_items_not_updated_since(
        self, cutoff_utc: datetime, store_names: list[str] | None = None
    ) -> int:
        """Delete from ``products`` where ``updated_at`` < cutoff; ``product_tags`` cascade."""
        self._ensure_client()
        if cutoff_utc.tzinfo is None:
            cutoff_utc = cutoff_utc.replace(tzinfo=timezone.utc)
        cutoff_utc = cutoff_utc.astimezone(timezone.utc)
        cutoff_iso = cutoff_utc.isoformat().replace("+00:00", "Z")

        q = self._client.table("products").delete().lt("updated_at", cutoff_iso)
        if store_names:
            q = q.in_("store", store_names)
        resp = q.select("id").execute()
        data = resp.data
        if data is None:
            return 0
        return len(data)
