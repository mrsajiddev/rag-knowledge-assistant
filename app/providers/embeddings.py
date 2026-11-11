"""Embedding providers: local Ollama or any OpenAI-compatible /embeddings API."""
from __future__ import annotations

from typing import List, Optional, Protocol

import httpx

from app.config import Settings


class ProviderError(RuntimeError):
    """Raised when a model provider is unreachable or returns an error."""


class Embedder(Protocol):
    model: str

    def embed_documents(self, texts: List[str]) -> List[List[float]]: ...

    def embed_query(self, text: str) -> List[float]: ...


def _check_vectors(vectors: List[List[float]], expected: int) -> List[List[float]]:
    if len(vectors) != expected or any(not v for v in vectors):
        raise ProviderError("Embedding provider returned an empty or incomplete result.")
    return vectors


class OllamaEmbedder:
    """Uses Ollama's batch endpoint (/api/embed), falling back to the legacy one."""

    def __init__(self, settings: Settings, client: Optional[httpx.Client] = None):
        self.model = settings.embed_model
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.batch_size = settings.embed_batch_size
        self.query_prefix = settings.query_prefix
        self.doc_prefix = settings.doc_prefix
        self.client = client or httpx.Client(timeout=settings.request_timeout)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            try:
                res = self.client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": batch},
                )
                if res.status_code == 404 and "model" not in res.text.lower():
                    vectors.extend(self._embed_legacy(batch))  # Ollama < 0.3.4
                    continue
                res.raise_for_status()
            except httpx.ConnectError as exc:
                raise ProviderError(
                    f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise ProviderError(
                    f"Ollama embedding error ({res.status_code}): {res.text[:300]}. "
                    f"Try `ollama pull {self.model}`."
                ) from exc
            vectors.extend(res.json().get("embeddings", []))
        return _check_vectors(vectors, len(texts))

    def _embed_legacy(self, texts: List[str]) -> List[List[float]]:
        out = []
        for text in texts:
            res = self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            res.raise_for_status()
            out.append(res.json()["embedding"])
        return out

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed([self.doc_prefix + t for t in texts])

    def embed_query(self, text: str) -> List[float]:
        return self._embed([self.query_prefix + text])[0]


class OpenAICompatibleEmbedder:
    """Works with OpenAI, Gemini (OpenAI-compat endpoint), OpenRouter, Together, etc."""

    def __init__(self, settings: Settings, client: Optional[httpx.Client] = None):
        if not settings.embed_base_url:
            raise ProviderError("EMBED_BASE_URL (or LLM_BASE_URL) must be set for EMBED_PROVIDER=openai.")
        self.model = settings.embed_model
        self.base_url = settings.embed_base_url.rstrip("/")
        self.api_key = settings.embed_api_key
        self.dimensions = settings.embed_dimensions
        self.batch_size = settings.embed_batch_size
        self.query_prefix = settings.query_prefix
        self.doc_prefix = settings.doc_prefix
        self.client = client or httpx.Client(timeout=settings.request_timeout)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        vectors: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            body = {"model": self.model, "input": texts[start:start + self.batch_size]}
            if self.dimensions:
                body["dimensions"] = self.dimensions
            try:
                res = self.client.post(f"{self.base_url}/embeddings", json=body, headers=headers)
                res.raise_for_status()
            except httpx.ConnectError as exc:
                raise ProviderError(f"Cannot reach embedding API at {self.base_url}.") from exc
            except httpx.HTTPStatusError as exc:
                raise ProviderError(
                    f"Embedding API error ({res.status_code}): {res.text[:300]}"
                ) from exc
            data = sorted(res.json()["data"], key=lambda d: d.get("index", 0))
            vectors.extend(d["embedding"] for d in data)
        return _check_vectors(vectors, len(texts))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed([self.doc_prefix + t for t in texts])

    def embed_query(self, text: str) -> List[float]:
        return self._embed([self.query_prefix + text])[0]


def build_embedder(settings: Settings) -> Embedder:
    if settings.embed_provider == "ollama":
        return OllamaEmbedder(settings)
    if settings.embed_provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleEmbedder(settings)
    raise ProviderError(f"Unknown EMBED_PROVIDER '{settings.embed_provider}'. Use 'ollama' or 'openai'.")
