"""FastAPI app: chat API (JSON + streaming) and the web chat page."""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque, Dict, Iterator, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import __version__
from app.config import Settings, get_settings
from app.db.vector_store import KnowledgeBaseMissing
from app.providers import ProviderError
from app.rag.pipeline import RAGPipeline
from app.db.vector_store import VectorStore
from app.services import get_pipeline, get_store

logger = logging.getLogger("nestora")
STATIC_DIR = Path(__file__).parent / "static"

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Retrieval-augmented chat over a Markdown knowledge base (FastAPI + Qdrant + Ollama/OpenAI-compatible LLMs).",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's question")
    history: List[ChatMessage] = Field(default_factory=list, description="Previous turns, oldest first")


class SourceOut(BaseModel):
    id: int
    title: str
    section: str
    source: str
    text: str
    score: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceOut]
    timing: Dict[str, int] = Field(default_factory=dict)
    model: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def rate_limit(request: Request, cfg: Settings = Depends(get_settings)) -> None:
    """Small in-memory sliding-window limiter (per process) for public demos."""
    limit = cfg.rate_limit_per_minute
    if limit <= 0:
        return
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "anon")
    now = time.monotonic()
    window = _hits[ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(status_code=429, detail="Too many questions in a minute. Wait a moment and try again.")
    window.append(now)


def validate(req: ChatRequest, cfg: Settings) -> str:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is empty.")
    if len(question) > cfg.max_question_chars:
        raise HTTPException(status_code=422, detail=f"Question is longer than {cfg.max_question_chars} characters.")
    return question


def history_of(req: ChatRequest) -> List[Dict[str, str]]:
    return [m.model_dump() for m in req.history]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health(cfg: Settings = Depends(get_settings), store: VectorStore = Depends(get_store)) -> dict:
    status = {"status": "ok", "version": __version__, **cfg.public_summary()}
    try:
        status["chunks"] = store.count()
        status["ready"] = status["chunks"] > 0
    except Exception as exc:  # vector DB unreachable
        status.update(status="degraded", ready=False, chunks=0, error=f"Vector database unreachable: {exc}")
    return status


@app.get("/api/documents")
def documents(store: VectorStore = Depends(get_store)) -> dict:
    try:
        docs = store.documents()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Vector database unreachable: {exc}")
    return {"documents": docs, "total_chunks": sum(d["chunks"] for d in docs)}


@app.post("/api/chat", response_model=ChatResponse, dependencies=[Depends(rate_limit)])
def chat(req: ChatRequest, cfg: Settings = Depends(get_settings), pipeline: RAGPipeline = Depends(get_pipeline)) -> dict:
    question = validate(req, cfg)
    try:
        result = pipeline.answer(question, history_of(req))
    except KnowledgeBaseMissing as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"question": question, **result}


@app.post("/api/chat/stream", dependencies=[Depends(rate_limit)])
def chat_stream(req: ChatRequest, cfg: Settings = Depends(get_settings), pipeline: RAGPipeline = Depends(get_pipeline)) -> StreamingResponse:
    """Server-Sent Events: `sources`, then many `token`, then `done` (or `error`)."""
    question = validate(req, cfg)
    history = history_of(req)

    def events() -> Iterator[str]:
        try:
            for event in pipeline.stream(question, history):
                yield f"data: {json.dumps(event)}\n\n"
        except (KnowledgeBaseMissing, ProviderError) as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except Exception:  # never leak a stack trace into the chat window
            logger.exception("Unexpected error while answering")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Something went wrong on the server. Check the server logs.'})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat", include_in_schema=False)
def legacy_chat(req: ChatRequest, cfg: Settings = Depends(get_settings), pipeline: RAGPipeline = Depends(get_pipeline)) -> dict:
    """Kept for backwards compatibility with the original v1 endpoint."""
    return chat(req, cfg, pipeline)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
