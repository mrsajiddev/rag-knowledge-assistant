"""Chat with the knowledge base from the terminal.

    python -m app.cli
"""
from __future__ import annotations

import sys
from typing import Dict, List

from app.config import get_settings
from app.db.vector_store import KnowledgeBaseMissing
from app.providers import ProviderError
from app.services import get_pipeline

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"


def main() -> None:
    settings = get_settings()
    pipeline = get_pipeline()
    history: List[Dict[str, str]] = []
    print(f"{BOLD}{settings.app_name}{RESET}  ({settings.llm_provider}:{settings.llm_model})")
    print(f"{DIM}Ask about {settings.kb_name}. Type /reset to clear the conversation, /quit to exit.{RESET}\n")

    while True:
        try:
            question = input(f"{BOLD}you ›{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question in {"/quit", "/exit"}:
            break
        if question == "/reset":
            history.clear()
            print(f"{DIM}Conversation cleared.{RESET}\n")
            continue

        print(f"{BOLD}bot ›{RESET} ", end="", flush=True)
        answer, sources, ms = [], [], 0
        try:
            for event in pipeline.stream(question, history):
                if event["type"] == "sources":
                    sources = event["sources"]
                elif event["type"] == "token":
                    answer.append(event["text"])
                    print(event["text"], end="", flush=True)
                elif event["type"] == "done":
                    ms = event["timing"]["total_ms"]
        except (KnowledgeBaseMissing, ProviderError) as exc:
            print(f"\nError: {exc}\n")
            continue
        except KeyboardInterrupt:
            print(f"\n{DIM}(stopped){RESET}\n")
            continue

        print()
        if sources:
            print(f"{DIM}Sources:")
            for s in sources:
                section = f" › {s['section']}" if s["section"] else ""
                print(f"  [{s['id']}] {s['title']}{section}  ({s['source']}, score {s['score']:.2f})")
            print(f"  {ms} ms{RESET}")
        print()
        history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": "".join(answer)}])


if __name__ == "__main__":
    sys.exit(main())
