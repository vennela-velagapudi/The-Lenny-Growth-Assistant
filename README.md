# The Lenny Growth Assistant

A full-stack AI conversational web application built as a Forward Deployed Engineer evaluation.

## Features
- AI conversational agent built with Anthropic Claude Agent SDK.
- Support for local inference via Ollama (default) and cloud models (Anthropic).
- RAG using Lenny's Podcast transcripts.
- Strict RAG grounding with source citations.
- Artifact generation and secure rendering (Markdown & HTML).
- PostgreSQL with pgvector for persistence and retrieval.

## Architecture

This project is structured as a FastAPI backend powered by PostgreSQL (`pgvector`).
- **Retrieval System**: Transcripts are ingested natively. Cosine distance retrieves the top-K semantic matches.
- **Conversational Agent**: We utilize the official **Anthropic Claude Agent SDK** for tool routing. A deterministic grounding policy short-circuits the LLM if evidence falls below the threshold, preventing hallucination.
- **LLM Provider Abstraction**: Supports both Anthropic Claude (via the SDK) and local execution via Ollama (using `/api/chat` native tools).

## Setup Instructions
1. Copy `.env.example` to `.env` and fill in necessary values.
2. Run `docker compose up --build` to start the application.
3. Access the frontend at `http://localhost:3000` (or the configured port).
4. Access the backend API docs at `http://localhost:8000/docs`.

### Transcript Data Source
For this project, we rely on the public repository:
[LennysNewsletter/lennys-newsletterpodcastdata](https://github.com/LennysNewsletter/lennys-newsletterpodcastdata)

To ingest transcripts:
1. Place markdown transcript files (`.md`) inside the `data/transcripts/` directory. (You can clone the repository above directly into this directory, or use `backend/scripts/download_samples.py`).
2. Run database migrations: `docker compose exec backend alembic upgrade head`
3. Pull the Ollama embedding model: `docker compose exec ollama ollama pull nomic-embed-text`
4. Run the ingestion command:
```bash
docker compose exec backend python scripts/ingest.py
```
*(Alternatively, run `python scripts/ingest.py` locally from the `backend` directory if outside Docker).*

If you do not have Docker/Ollama, ingestion will fail to generate embeddings unless a mocked environment is configured.

### Testing the API
Session creation and agent execution can be hit directly via the REST API endpoints:
- `POST /api/sessions` (Create a chat session)
- `POST /api/sessions/{session_id}/messages` (Send a message and trigger the agent loop)
