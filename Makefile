.PHONY: install qdrant models ingest run chat test docker

install:            ## Create the virtualenv and install dependencies
	python3 -m venv venv && ./venv/bin/pip install -r requirements-dev.txt

qdrant:             ## Start Qdrant in Docker
	docker compose up -d qdrant

models:             ## Download the default local models
	ollama pull qwen3:8b && ollama pull nomic-embed-text

ingest:             ## Index the knowledge base
	./venv/bin/python -m app.ingest

run:                ## Start the web app with auto-reload on http://localhost:8000
	./venv/bin/uvicorn app.main:app --reload --port 8000

chat:               ## Chat in the terminal
	./venv/bin/python -m app.cli

test:               ## Run the test suite (no models or Qdrant needed)
	./venv/bin/python -m pytest -q

docker:             ## Run Qdrant and the app in Docker
	docker compose up -d --build
