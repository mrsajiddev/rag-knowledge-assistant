"""Test fixtures: an in-memory Qdrant plus fake embedding and chat models.

The fake embedder hashes words into a fixed-size vector, so texts that share
words get similar vectors. That's enough to test retrieval end to end without
Ollama or any API key.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Iterator, List

import pytest
from fastapi.testclient import TestClient

from app.config import PROJECT_ROOT, Settings
from app.db.vector_store import VectorStore
from app.ingest import run as run_ingest
from app.main import app
from app.rag.pipeline import STOPWORDS, RAGPipeline
from app.services import get_pipeline, get_store

DIM = 256


class HashEmbedder:
    model = "fake-hash-embed"

    def _vec(self, text: str) -> List[float]:
        v = [0.0] * DIM
        for word in re.findall(r"[a-z0-9\-]{3,}", text.lower()):
            if word in STOPWORDS:
                continue
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            v[h % DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vec(text)


class EchoChat:
    """Returns a deterministic answer that cites the first passage."""

    model = "fake-chat"

    def __init__(self) -> None:
        self.last_messages = None

    def stream(self, messages) -> Iterator[str]:
        self.last_messages = messages
        has_context = "No relevant passages" not in messages[0]["content"]
        text = "<think>internal reasoning</think>Here is the answer [1]." if has_context else "I could not find that."
        for i in range(0, len(text), 7):
            yield text[i:i + 7]


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(qdrant_url=None, qdrant_path=None, min_score=0.1, rate_limit_per_minute=0)


@pytest.fixture(scope="session")
def store(settings) -> VectorStore:
    vs = VectorStore(settings)  # in-memory
    import app.ingest as ingest_mod
    original = ingest_mod.get_settings
    ingest_mod.get_settings = lambda: settings
    try:
        run_ingest(PROJECT_ROOT / "knowledge_base", store=vs, embedder=HashEmbedder())
    finally:
        ingest_mod.get_settings = original
    return vs


@pytest.fixture()
def pipeline(settings, store) -> RAGPipeline:
    return RAGPipeline(settings, HashEmbedder(), EchoChat(), store)


@pytest.fixture()
def client(pipeline, store):
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
