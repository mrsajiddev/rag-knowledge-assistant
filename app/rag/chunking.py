"""Loading and chunking documents.

Chunks follow the structure of the document: Markdown is split by heading
first, then paragraphs are packed into chunks of roughly `chunk_size`
characters with a small overlap. Fenced code blocks and tables are never cut
in half. Each chunk remembers its document title and heading path, which is
prepended before embedding ("contextual chunk headers") so a passage like
"It costs $49/month" still carries the context "Pricing > Growth plan".
"""
from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf"}
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*#*\s*$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Document:
    source: str  # path relative to the knowledge base folder
    title: str
    text: str


@dataclass
class Chunk:
    source: str
    title: str
    section: str
    text: str
    index: int
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        digest = hashlib.sha1(f"{self.source}|{self.index}|{self.text}".encode()).hexdigest()
        return str(uuid.UUID(digest[:32]))

    def embedding_text(self) -> str:
        header = self.title if not self.section or self.section == self.title else f"{self.title} > {self.section}"
        return f"{header}\n\n{self.text}"

    def payload(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "section": self.section,
            "text": self.text,
            "chunk_index": self.index,
            **self.metadata,
        }


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _title_from_filename(path: Path) -> str:
    name = re.sub(r"^\d+[-_ ]*", "", path.stem)
    return name.replace("-", " ").replace("_", " ").strip().capitalize() or path.stem


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install pypdf to ingest PDF files: pip install pypdf") from exc
    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)


def load_document(path: Path, root: Path) -> Optional[Document]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return None
    text = _read_pdf(path) if suffix == ".pdf" else path.read_text(encoding="utf-8", errors="ignore")
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return None
    title = _title_from_filename(path)
    first = HEADING_RE.match(text.splitlines()[0])
    if first and len(first.group(1)) == 1:
        title = first.group(2).strip()
    return Document(source=path.relative_to(root).as_posix(), title=title, text=text)


def load_documents(root: Path) -> List[Document]:
    if not root.exists():
        raise FileNotFoundError(f"Knowledge base folder not found: {root}")
    docs = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.name.startswith(".") and path.name.lower() != "readme.md":
            doc = load_document(path, root)
            if doc:
                docs.append(doc)
    return docs


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _split_sections(doc: Document):
    """Yield (heading_path, body) pairs. The H1 title is not repeated in the path."""
    path: List[str] = []
    levels: List[int] = []
    body: List[str] = []
    in_fence = False

    def flush():
        text = "\n".join(body).strip()
        if text:
            yield_list.append((" > ".join(path), text))
        body.clear()

    yield_list: List[tuple] = []
    for line in doc.text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else HEADING_RE.match(line)
        if match:
            flush()
            level, heading = len(match.group(1)), match.group(2).strip()
            if level == 1:
                path, levels = [], []
                continue
            while levels and levels[-1] >= level:
                levels.pop()
                path.pop()
            levels.append(level)
            path.append(heading)
        else:
            body.append(line)
    flush()
    return yield_list


def _blocks(text: str) -> List[str]:
    """Split into paragraphs while keeping code fences and tables intact."""
    blocks, current, in_fence = [], [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _split_long(block: str, size: int) -> List[str]:
    if len(block) <= size:
        return [block]
    if block.lstrip().startswith(("```", "|")):
        lines, parts, buf = block.splitlines(), [], ""
        for line in lines:
            if buf and len(buf) + len(line) + 1 > size:
                parts.append(buf)
                buf = ""
            buf = f"{buf}\n{line}" if buf else line
        return parts + ([buf] if buf else [])
    parts, buf = [], ""
    for sentence in SENTENCE_RE.split(block):
        while len(sentence) > size:  # pathological: no punctuation at all
            parts.append(sentence[:size])
            sentence = sentence[size:]
        if buf and len(buf) + len(sentence) + 1 > size:
            parts.append(buf)
            buf = ""
        buf = f"{buf} {sentence}" if buf else sentence
    return parts + ([buf] if buf else [])


def chunk_document(doc: Document, chunk_size: int = 900, overlap: int = 150) -> List[Chunk]:
    chunks: List[Chunk] = []
    for section, body in _split_sections(doc):
        pieces: List[str] = []
        for block in _blocks(body):
            pieces.extend(_split_long(block, chunk_size))

        current: List[str] = []
        for piece in pieces:
            size = sum(len(p) + 2 for p in current)
            if current and size + len(piece) > chunk_size:
                chunks.append(Chunk(doc.source, doc.title, section, "\n\n".join(current), len(chunks)))
                # carry trailing pieces forward as overlap
                carry: List[str] = []
                for prev in reversed(current):
                    if sum(len(c) for c in carry) + len(prev) > overlap:
                        break
                    carry.insert(0, prev)
                current = carry
            current.append(piece)
        if current:
            chunks.append(Chunk(doc.source, doc.title, section, "\n\n".join(current), len(chunks)))
    return chunks


def chunk_documents(docs: List[Document], chunk_size: int = 900, overlap: int = 150) -> List[Chunk]:
    out: List[Chunk] = []
    for doc in docs:
        out.extend(chunk_document(doc, chunk_size, overlap))
    return out
