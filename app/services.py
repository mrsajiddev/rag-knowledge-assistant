"""Lazily-built singletons shared by the API, the CLI and ingestion."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.db.vector_store import VectorStore
from app.providers import build_chat_model, build_embedder
from app.rag.pipeline import RAGPipeline


@lru_cache(maxsize=1)
def get_store() -> VectorStore:
    return VectorStore(get_settings())


@lru_cache(maxsize=1)
def get_pipeline() -> RAGPipeline:
    settings = get_settings()
    return RAGPipeline(settings, build_embedder(settings), build_chat_model(settings), get_store())
