"""Application settings, read from environment variables (and a local .env file).

Every setting has a sensible default for the fully local setup
(Ollama + Qdrant on localhost), so `.env` is optional when running locally.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    return int(value) if value is not None else default


def _env_float(name: str, default: float) -> float:
    value = _env(name)
    return float(value) if value is not None else default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # --- Branding -------------------------------------------------------
    app_name: str = "Nestora Assistant"
    kb_name: str = "Nestora Commerce"

    # --- Chat model -----------------------------------------------------
    # "ollama" for local models, "openai" for any OpenAI-compatible API
    # (OpenAI, Groq, Google Gemini, OpenRouter, Together, LM Studio, vLLM...).
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:8b"
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 1024
    ollama_think: bool = False  # Qwen3 / DeepSeek-R1 "thinking" output

    # --- Embedding model --------------------------------------------------
    embed_provider: str = "ollama"
    embed_model: str = "nomic-embed-text"
    embed_base_url: Optional[str] = None
    embed_api_key: Optional[str] = None
    embed_dimensions: Optional[int] = None
    embed_batch_size: int = 32
    embed_query_prefix: Optional[str] = None
    embed_doc_prefix: Optional[str] = None

    ollama_base_url: str = "http://localhost:11434"
    request_timeout: float = 120.0

    # --- Vector database --------------------------------------------------
    qdrant_url: Optional[str] = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_path: Optional[str] = None  # embedded mode, no server needed
    collection_name: str = "knowledge_base"

    # --- Retrieval --------------------------------------------------------
    kb_dir: str = "knowledge_base"
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5
    candidates: int = 20
    min_score: float = 0.35
    history_turns: int = 6

    # --- Web server -------------------------------------------------------
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    max_question_chars: int = 2000
    rate_limit_per_minute: int = 30  # per client IP, 0 disables

    @property
    def query_prefix(self) -> str:
        if self.embed_query_prefix is not None:
            return self.embed_query_prefix
        return "search_query: " if "nomic" in self.embed_model.lower() else ""

    @property
    def doc_prefix(self) -> str:
        if self.embed_doc_prefix is not None:
            return self.embed_doc_prefix
        return "search_document: " if "nomic" in self.embed_model.lower() else ""

    @property
    def kb_path(self) -> Path:
        path = Path(self.kb_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    def public_summary(self) -> dict:
        """Non-secret configuration, safe to expose on /api/health."""
        if self.qdrant_url:
            store = "qdrant-cloud" if "cloud.qdrant.io" in self.qdrant_url else "qdrant-server"
        else:
            store = "qdrant-embedded"
        return {
            "app_name": self.app_name,
            "kb_name": self.kb_name,
            "llm": {"provider": self.llm_provider, "model": self.llm_model},
            "embeddings": {"provider": self.embed_provider, "model": self.embed_model},
            "vector_store": store,
            "collection": self.collection_name,
            "top_k": self.top_k,
        }


def load_settings() -> Settings:
    llm_provider = (_env("LLM_PROVIDER", "ollama") or "ollama").lower()
    embed_provider = (_env("EMBED_PROVIDER", "ollama") or "ollama").lower()
    llm_base_url = _env("LLM_BASE_URL")
    llm_api_key = _env("LLM_API_KEY")
    qdrant_path = _env("QDRANT_PATH")
    dims = _env("EMBED_DIMENSIONS")

    return Settings(
        app_name=_env("APP_NAME", "Nestora Assistant"),
        kb_name=_env("KB_NAME", "Nestora Commerce"),
        llm_provider=llm_provider,
        llm_model=_env("LLM_MODEL", "qwen3:8b"),
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        temperature=_env_float("TEMPERATURE", 0.2),
        max_tokens=_env_int("MAX_TOKENS", 1024),
        ollama_think=_env_bool("OLLAMA_THINK", False),
        embed_provider=embed_provider,
        embed_model=_env("EMBED_MODEL", "nomic-embed-text"),
        # Embeddings fall back to the chat endpoint/key when not set separately.
        embed_base_url=_env("EMBED_BASE_URL", llm_base_url),
        embed_api_key=_env("EMBED_API_KEY", llm_api_key),
        embed_dimensions=int(dims) if dims else None,
        embed_batch_size=_env_int("EMBED_BATCH_SIZE", 32),
        embed_query_prefix=os.getenv("EMBED_QUERY_PREFIX"),
        embed_doc_prefix=os.getenv("EMBED_DOC_PREFIX"),
        ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        request_timeout=_env_float("REQUEST_TIMEOUT", 120.0),
        # An explicit QDRANT_PATH switches to embedded mode unless a URL is also set.
        qdrant_url=_env("QDRANT_URL", None if qdrant_path else "http://localhost:6333"),
        qdrant_api_key=_env("QDRANT_API_KEY"),
        qdrant_path=qdrant_path,
        collection_name=_env("COLLECTION_NAME", "knowledge_base"),
        kb_dir=_env("KB_DIR", "knowledge_base"),
        chunk_size=_env_int("CHUNK_SIZE", 900),
        chunk_overlap=_env_int("CHUNK_OVERLAP", 150),
        top_k=_env_int("TOP_K", 5),
        candidates=_env_int("CANDIDATES", 20),
        min_score=_env_float("MIN_SCORE", 0.35),
        history_turns=_env_int("HISTORY_TURNS", 6),
        cors_origins=[o.strip() for o in (_env("CORS_ORIGINS", "*") or "*").split(",")],
        max_question_chars=_env_int("MAX_QUESTION_CHARS", 2000),
        rate_limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 30),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
