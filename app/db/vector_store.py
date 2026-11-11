"""Thin wrapper around Qdrant.

Supports three modes, picked from settings:
  * Qdrant server   QDRANT_URL=http://localhost:6333   (Docker)
  * Qdrant Cloud    QDRANT_URL=https://xxx.cloud.qdrant.io + QDRANT_API_KEY
  * Embedded        QDRANT_PATH=./.qdrant            (no server at all)
"""
from __future__ import annotations

import atexit
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import Settings


class KnowledgeBaseMissing(RuntimeError):
    """The collection does not exist yet: run the ingestion step."""


@dataclass
class Hit:
    id: str
    score: float
    payload: dict


class VectorStore:
    def __init__(self, settings: Settings, client: Optional[QdrantClient] = None):
        self.collection = settings.collection_name
        if client is not None:
            self.client = client
        elif settings.qdrant_url:
            self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30)
        elif settings.qdrant_path:
            self.client = QdrantClient(path=settings.qdrant_path)
            atexit.register(self.client.close)  # release the folder lock cleanly
        else:
            self.client = QdrantClient(location=":memory:")
        self._documents_cache: Optional[List[dict]] = None

    # -- write ---------------------------------------------------------------
    def recreate(self, dimension: int) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
        self._documents_cache = None

    def upsert(self, points: List[PointStruct], batch_size: int = 128) -> None:
        for start in range(0, len(points), batch_size):
            self.client.upsert(collection_name=self.collection, points=points[start:start + batch_size])
        self._documents_cache = None

    # -- read ----------------------------------------------------------------
    def exists(self) -> bool:
        return self.client.collection_exists(self.collection)

    def count(self) -> int:
        if not self.exists():
            return 0
        return self.client.count(self.collection, exact=True).count

    def dimension(self) -> Optional[int]:
        if not self.exists():
            return None
        vectors = self.client.get_collection(self.collection).config.params.vectors
        return getattr(vectors, "size", None)

    def search(self, vector: List[float], limit: int) -> List[Hit]:
        if not self.exists():
            raise KnowledgeBaseMissing(
                f"Collection '{self.collection}' not found. Run `python -m app.ingest` first."
            )
        expected = self.dimension()
        if expected and expected != len(vector):
            raise KnowledgeBaseMissing(
                f"The collection holds {expected}-dim vectors but the embedding model returned "
                f"{len(vector)} dims. Re-run `python -m app.ingest` after changing EMBED_MODEL."
            )
        result = self.client.query_points(
            collection_name=self.collection, query=vector, limit=limit, with_payload=True
        )
        return [Hit(id=str(p.id), score=float(p.score), payload=p.payload or {}) for p in result.points]

    def documents(self) -> List[dict]:
        """Distinct source documents in the collection with chunk counts (cached)."""
        if self._documents_cache is not None:
            return self._documents_cache
        if not self.exists():
            return []
        docs: Dict[str, dict] = OrderedDict()
        offset = None
        while True:
            points, offset = self.client.scroll(
                self.collection,
                limit=256,
                offset=offset,
                with_payload=["source", "title"],
                with_vectors=False,
            )
            for p in points:
                payload = p.payload or {}
                source = payload.get("source", "unknown")
                entry = docs.setdefault(source, {"source": source, "title": payload.get("title", source), "chunks": 0})
                entry["chunks"] += 1
            if offset is None:
                break
        self._documents_cache = sorted(docs.values(), key=lambda d: d["source"])
        return self._documents_cache
