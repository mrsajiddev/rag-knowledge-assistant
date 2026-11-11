"""Chat model providers with token streaming: local Ollama or any OpenAI-compatible API."""
from __future__ import annotations

import json
from typing import Dict, Iterator, List, Optional, Protocol

import httpx

from app.config import Settings
from app.providers.embeddings import ProviderError

Message = Dict[str, str]


class ChatModel(Protocol):
    model: str

    def stream(self, messages: List[Message]) -> Iterator[str]: ...


class ThinkFilter:
    """Removes <think>...</think> blocks from a token stream.

    Reasoning models (Qwen3, DeepSeek-R1) may emit their chain of thought
    inline. Tags can be split across tokens, so we buffer just enough text
    to recognise them.
    """

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.buffer = ""
        self.inside = False
        self.started = False  # strip leading whitespace after a think block

    def feed(self, text: str) -> str:
        self.buffer += text
        out = []
        while self.buffer:
            tag = self.CLOSE if self.inside else self.OPEN
            idx = self.buffer.find(tag)
            if idx >= 0:
                if not self.inside:
                    out.append(self.buffer[:idx])
                self.buffer = self.buffer[idx + len(tag):]
                self.inside = not self.inside
                continue
            # Keep a possible partial tag at the end of the buffer.
            keep = 0
            for i in range(1, len(tag)):
                if self.buffer.endswith(tag[:i]):
                    keep = i
            emit, self.buffer = self.buffer[:len(self.buffer) - keep], self.buffer[len(self.buffer) - keep:]
            if not self.inside:
                out.append(emit)
            break
        result = "".join(out)
        if not self.started:
            result = result.lstrip()
            self.started = bool(result)
        return result

    def flush(self) -> str:
        rest = "" if self.inside else self.buffer
        self.buffer = ""
        return rest


class OllamaChat:
    def __init__(self, settings: Settings, client: Optional[httpx.Client] = None):
        self.model = settings.llm_model
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        self.think = settings.ollama_think
        self.client = client or httpx.Client(timeout=settings.request_timeout)
        self._think_supported = True

    def _body(self, messages: List[Message]) -> dict:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        if self._think_supported:
            body["think"] = self.think
        return body

    def stream(self, messages: List[Message]) -> Iterator[str]:
        for attempt in range(2):
            try:
                with self.client.stream("POST", f"{self.base_url}/api/chat", json=self._body(messages)) as res:
                    if res.status_code >= 400:
                        detail = res.read().decode(errors="ignore")
                        if "think" in detail.lower() and self._think_supported and attempt == 0:
                            self._think_supported = False  # older Ollama / non-thinking model
                            continue
                        raise ProviderError(
                            f"Ollama chat error ({res.status_code}): {detail[:300]}. "
                            f"Try `ollama pull {self.model}`."
                        )
                    for line in res.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise ProviderError(f"Ollama: {data['error']}")
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            return
                    return
            except httpx.ConnectError as exc:
                raise ProviderError(
                    f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
                ) from exc


class OpenAICompatibleChat:
    def __init__(self, settings: Settings, client: Optional[httpx.Client] = None):
        if not settings.llm_base_url:
            raise ProviderError("LLM_BASE_URL must be set for LLM_PROVIDER=openai.")
        self.model = settings.llm_model
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        self.client = client or httpx.Client(timeout=settings.request_timeout)

    def stream(self, messages: List[Message]) -> Iterator[str]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        try:
            with self.client.stream("POST", f"{self.base_url}/chat/completions", json=body, headers=headers) as res:
                if res.status_code >= 400:
                    detail = res.read().decode(errors="ignore")
                    raise ProviderError(f"LLM API error ({res.status_code}): {detail[:300]}")
                for line in res.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        return
                    data = json.loads(payload)
                    choices = data.get("choices") or []
                    if choices:
                        token = (choices[0].get("delta") or {}).get("content")
                        if token:
                            yield token
        except httpx.ConnectError as exc:
            raise ProviderError(f"Cannot reach LLM API at {self.base_url}.") from exc


def build_chat_model(settings: Settings) -> ChatModel:
    if settings.llm_provider == "ollama":
        return OllamaChat(settings)
    if settings.llm_provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleChat(settings)
    raise ProviderError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use 'ollama' or 'openai'.")
