# Knowledge base

This folder is indexed by `python -m app.ingest`. Every `.md`, `.txt` and `.pdf`
file in it (including sub-folders) becomes searchable. This README is skipped.

The bundled content documents **Nestora Commerce**, a fictional e-commerce
platform invented for this demo. All names, prices, policies, people, domains
(`*.nestora.example`) and partner companies are made up. A fictional company is
used deliberately: an LLM cannot know these answers from its training data, so
every correct answer demonstrates that retrieval is working.

To use your own content, delete these files, add yours, and re-run ingestion.
Markdown with clear `##` headings gives the best results, because each chunk
remembers the heading it came from.
