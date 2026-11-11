from pathlib import Path

from app.config import PROJECT_ROOT
from app.rag.chunking import Document, chunk_document, load_documents


def test_knowledge_base_loads_and_skips_readme():
    docs = load_documents(PROJECT_ROOT / "knowledge_base")
    sources = {d.source for d in docs}
    assert len(docs) >= 15
    assert "README.md" not in sources
    assert "internal/16-employee-handbook.md" in sources


def test_sections_follow_heading_path():
    doc = Document("x.md", "fallback", "# Pricing\n\n## Growth plan\n\nCosts $49.\n\n### Limits\n\n10 staff.")
    chunks = chunk_document(doc)
    assert [c.section for c in chunks] == ["Growth plan", "Growth plan > Limits"]
    assert chunks[0].embedding_text().startswith("fallback > Growth plan")


def test_chunks_respect_size_and_keep_code_fences_whole():
    code = "```php\n" + "\n".join(f"$a{i} = {i};" for i in range(20)) + "\n```"
    text = "# Doc\n\n## Part\n\n" + "\n\n".join(["Sentence number %d is here." % i for i in range(80)]) + "\n\n" + code
    chunks = chunk_document(Document("d.md", "Doc", text), chunk_size=400, overlap=80)
    assert len(chunks) > 3
    assert all(len(c.text) <= 480 for c in chunks)
    fenced = [c.text for c in chunks if "```php" in c.text]
    assert fenced and all(t.count("```") == 2 for t in fenced)


def test_overlap_repeats_context_between_neighbours():
    paras = [f"Paragraph {i} " + "word " * 20 for i in range(10)]
    chunks = chunk_document(Document("d.md", "Doc", "\n\n".join(paras)), chunk_size=300, overlap=150)
    assert chunks[1].text.split("\n\n")[0] in chunks[0].text


def test_chunk_ids_are_stable():
    doc = Document("d.md", "Doc", "Hello world. " * 10)
    assert [c.id for c in chunk_document(doc)] == [c.id for c in chunk_document(doc)]
