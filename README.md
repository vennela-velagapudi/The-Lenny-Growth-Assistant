# The Lenny Growth Assistant

A full-stack AI conversational web application built as a Forward Deployed Engineer evaluation.

## Features
- AI conversational agent built with Anthropic Claude Agent SDK.
- Support for local inference via Ollama (default) and cloud models (Anthropic).
- RAG using Lenny's Podcast transcripts.
- Strict RAG grounding with source citations.
- Artifact generation and secure rendering (Markdown & HTML).
- PostgreSQL with pgvector for persistence and retrieval.

## Setup Instructions
1. Copy `.env.example` to `.env` and fill in necessary values.
2. Run `docker compose up --build` to start the application.
3. Access the frontend at `http://localhost:3000` (or the configured port).
4. Access the backend API docs at `http://localhost:8000/docs`.

### Ingestion
To ingest transcripts into the knowledge base, run:
```bash
docker compose exec backend python scripts/ingest.py
```
*(Ingestion requires the data/transcripts folder to be populated with markdown/text files).*
