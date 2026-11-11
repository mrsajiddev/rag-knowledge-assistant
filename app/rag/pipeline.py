"""Retrieval-augmented generation: retrieve -> rerank -> prompt -> stream."""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from typing import Dict, Iterator, List, Optional

from app.config import Settings
from app.db.vector_store import Hit, VectorStore
from app.providers import ChatModel, Embedder, ThinkFilter

STOPWORDS = set(
    """a an the and or but if of to in on at by for with from as is are was were be been being
    it its this that these those i you he she we they me my your our their do does did can could
    should would will shall may might must have has had not no yes how what when where which who
    whom why about into over under than then there here so very just also any all each some such
    more most other only own same too out up down off again further once get got use using""".split()
)
CODE_RE = re.compile(r"\b[A-Z]{2,5}-\d{2,5}\b")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9_\-]{2,}")

SYSTEM_PROMPT = """You are {app_name}, a knowledge assistant for {kb_name}.

Answer the user's question using ONLY the numbered context passages below.
- Cite the passages you used inline with their number in square brackets, e.g. "Payouts run every Tuesday [2]." Never cite a number that is not listed.
- If the passages do not contain the answer, say plainly that the knowledge base does not cover it and, if helpful, suggest a related question it can answer. Never invent facts, prices, limits or policies.
- For greetings or questions about what you can do, reply briefly and mention the topics the knowledge base covers.
- Format with Markdown: short paragraphs, bullet or numbered lists for steps, fenced code blocks for code. Keep answers focused; no preamble.

Context passages:
{context}"""

NO_CONTEXT = "(No relevant passages were found in the knowledge base for this question.)"


@dataclass
class Source:
    id: int
    title: str
    section: str
    source: str
    text: str
    score: float

    def to_dict(self) -> dict:
        data = asdict(self)
        data["score"] = round(self.score, 4)
        return data


def keywords(text: str) -> set:
    return {w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS}


def rerank(query: str, hits: List[Hit], min_score: float, top_k: int) -> List[Hit]:
    """Hybrid scoring: vector similarity plus a small lexical bonus.

    Dense embeddings are weak at exact identifiers (error codes, plan names,
    API paths). A cheap keyword-overlap bonus fixes most of those misses
    without a second index.
    """
    terms = keywords(query)
    codes = {c.upper() for c in CODE_RE.findall(query.upper())}
    scored = []
    for hit in hits:
        p = hit.payload
        haystack = f"{p.get('title', '')} {p.get('section', '')} {p.get('text', '')}"
        overlap = len(terms & keywords(haystack)) / len(terms) if terms else 0.0
        code_match = bool(codes) and any(code in haystack.upper() for code in codes)
        if hit.score < min_score and not code_match:
            continue
        final = hit.score + 0.15 * overlap + (0.25 if code_match else 0.0)
        scored.append((final, hit))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [Hit(id=h.id, score=s, payload=h.payload) for s, h in scored[:top_k]]


class RAGPipeline:
    def __init__(self, settings: Settings, embedder: Embedder, llm: ChatModel, store: VectorStore):
        self.settings = settings
        self.embedder = embedder
        self.llm = llm
        self.store = store

    # -- retrieval -----------------------------------------------------------
    def retrieve(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> List[Source]:
        s = self.settings
        merged: Dict[str, Hit] = {}
        queries = [question]
        # Follow-ups like "and on the Growth plan?" need the previous question for context.
        last_user = next((m["content"] for m in reversed(history or []) if m.get("role") == "user"), None)
        if last_user:
            queries.append(f"{last_user[:300]}\n{question}")
        for q in queries:
            for hit in self.store.search(self.embedder.embed_query(q), limit=s.candidates):
                if hit.id not in merged or hit.score > merged[hit.id].score:
                    merged[hit.id] = hit
        ranked = rerank(" ".join(queries), list(merged.values()), s.min_score, s.top_k)
        return [
            Source(
                id=i + 1,
                title=h.payload.get("title", ""),
                section=h.payload.get("section", ""),
                source=h.payload.get("source", ""),
                text=h.payload.get("text", ""),
                score=h.score,
            )
            for i, h in enumerate(ranked)
        ]

    # -- prompting -----------------------------------------------------------
    def build_messages(self, question: str, sources: List[Source], history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        if sources:
            context = "\n\n".join(
                f"[{src.id}] {src.title}{' > ' + src.section if src.section else ''}\n{src.text}"
                for src in sources
            )
        else:
            context = NO_CONTEXT
        system = SYSTEM_PROMPT.format(app_name=self.settings.app_name, kb_name=self.settings.kb_name, context=context)
        messages = [{"role": "system", "content": system}]
        turns = (history or [])[-self.settings.history_turns * 2:]
        for msg in turns:
            if msg.get("role") in {"user", "assistant"} and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"][:4000]})
        messages.append({"role": "user", "content": question})
        return messages

    # -- generation ----------------------------------------------------------
    def stream(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> Iterator[dict]:
        """Yields events: sources -> token* -> done (or error)."""
        started = time.perf_counter()
        sources = self.retrieve(question, history)
        retrieval_ms = int((time.perf_counter() - started) * 1000)
        yield {"type": "sources", "sources": [s.to_dict() for s in sources]}

        think = ThinkFilter()
        for token in self.llm.stream(self.build_messages(question, sources, history)):
            text = think.feed(token)
            if text:
                yield {"type": "token", "text": text}
        tail = think.flush()
        if tail:
            yield {"type": "token", "text": tail}
        yield {
            "type": "done",
            "timing": {
                "retrieval_ms": retrieval_ms,
                "total_ms": int((time.perf_counter() - started) * 1000),
            },
            "model": self.llm.model,
        }

    def answer(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> dict:
        answer, sources, meta = [], [], {}
        for event in self.stream(question, history):
            if event["type"] == "sources":
                sources = event["sources"]
            elif event["type"] == "token":
                answer.append(event["text"])
            elif event["type"] == "done":
                meta = event
        return {
            "answer": "".join(answer).strip(),
            "sources": sources,
            "timing": meta.get("timing", {}),
            "model": meta.get("model"),
        }
