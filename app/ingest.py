"""Build the vector index from the knowledge base folder.

    python -m app.ingest                 # index ./knowledge_base
    python -m app.ingest --dir ./my_docs # index another folder
    python -m app.ingest --dry-run       # show chunk stats only, no model calls
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

from qdrant_client.models import PointStruct

from app.config import get_settings
from app.db.vector_store import VectorStore
from app.providers import ProviderError, build_embedder
from app.rag.chunking import chunk_documents, load_documents


def run(directory: Path, dry_run: bool = False, store: VectorStore = None, embedder=None) -> int:
    settings = get_settings()
    docs = load_documents(directory)
    if not docs:
        print(f"No .md, .txt or .pdf files found in {directory}")
        return 1
    chunks = chunk_documents(docs, settings.chunk_size, settings.chunk_overlap)
    sizes = [len(c.text) for c in chunks]
    print(f"Loaded {len(docs)} documents from {directory}")
    print(f"Split into {len(chunks)} chunks (avg {sum(sizes) // len(sizes)} chars, max {max(sizes)})")

    if dry_run:
        per_doc = Counter(c.source for c in chunks)
        for doc in docs:
            print(f"  {per_doc[doc.source]:>3}  {doc.source}  ({doc.title})")
        return 0

    embedder = embedder or build_embedder(settings)
    store = store or VectorStore(settings)
    print(f"Embedding with {getattr(embedder, 'model', settings.embed_model)} ...")
    started = time.perf_counter()
    vectors = []
    batch = max(1, settings.embed_batch_size)
    for start in range(0, len(chunks), batch):
        part = chunks[start:start + batch]
        vectors.extend(embedder.embed_documents([c.embedding_text() for c in part]))
        done = min(start + batch, len(chunks))
        print(f"\r  {done}/{len(chunks)} chunks embedded", end="", flush=True)
    print()

    dimension = len(vectors[0])
    store.recreate(dimension)
    store.upsert([
        PointStruct(id=chunk.id, vector=vector, payload=chunk.payload())
        for chunk, vector in zip(chunks, vectors)
    ])
    elapsed = time.perf_counter() - started
    print(f"Stored {len(chunks)} vectors ({dimension} dims) in collection "
          f"'{settings.collection_name}' in {elapsed:.1f}s")
    return 0


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Index documents into Qdrant.")
    parser.add_argument("--dir", type=Path, default=settings.kb_path, help="Folder with .md/.txt/.pdf files")
    parser.add_argument("--dry-run", action="store_true", help="Only load and chunk, no embeddings")
    args = parser.parse_args()
    try:
        sys.exit(run(args.dir.resolve(), args.dry_run))
    except ProviderError as exc:
        print(f"\nError: {exc}")
        sys.exit(2)
    except Exception as exc:
        if "Connection refused" in str(exc) or "ConnectError" in type(exc).__name__:
            print(f"\nError: cannot reach Qdrant ({exc}). Start it with `docker compose up -d qdrant` "
                  "or set QDRANT_PATH=./.qdrant to use embedded mode.")
            sys.exit(2)
        raise


if __name__ == "__main__":
    main()
