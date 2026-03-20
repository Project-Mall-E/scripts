"""Firestore implementation of StorageProvider."""

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import StorageProvider
from .common import item_to_dict


def _url_to_document_id(url: str) -> str:
    """Encode URL as a Firestore-safe document ID (base64url, no padding)."""
    encoded = base64.urlsafe_b64encode(url.encode("utf-8")).rstrip(b"=")
    return encoded.decode("ascii")


def _document_id_to_url(doc_id: str) -> str:
    """Decode document ID back to URL."""
    padding = 4 - (len(doc_id) % 4)
    if padding != 4:
        doc_id += "=" * padding
    return base64.urlsafe_b64decode(doc_id.encode("ascii")).decode("utf-8")


class FirestoreStorageProvider(StorageProvider):
    """Persist items to Firestore collection store-items."""

    def __init__(
        self,
        credentials_path: str | Path | None = None,
        collection_name: str = "store-items",
    ) -> None:
        if credentials_path is None:
            package_root = Path(__file__).resolve().parent.parent
            credentials_path = package_root / "secrets" / "firebase-serviceaccount.json"
        self._credentials_path = Path(credentials_path)
        self._collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        import firebase_admin
        from firebase_admin import credentials, firestore

        try:
            firebase_admin.get_app()
        except ValueError:
            cred = credentials.Certificate(str(self._credentials_path))
            firebase_admin.initialize_app(cred)
        self._client = firestore.client()
        self._collection = self._client.collection(self._collection_name)

    def upsert(self, item: Any) -> None:
        self._ensure_client()
        data = item_to_dict(item)
        url = data.get("item_link")
        if not url:
            raise ValueError("item must have an 'item_link' field")
        doc_id = _url_to_document_id(url)
        doc_ref = self._collection.document(doc_id)
        snapshot = doc_ref.get()
        now = datetime.now(timezone.utc)
        if not snapshot.exists:
            payload = {
                **data,
                "inserted_time": now,
                "updated_time": now,
            }
            doc_ref.set(payload)
        else:
            update_payload = {
                **data,
                "updated_time": now,
            }
            doc_ref.update(update_payload)

    def get_by_url(self, url: str) -> dict | None:
        self._ensure_client()
        doc_id = _url_to_document_id(url)
        doc_ref = self._collection.document(doc_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        d = snapshot.to_dict()
        if d is None:
            return None
        return dict(d)
