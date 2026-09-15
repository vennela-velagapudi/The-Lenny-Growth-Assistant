# Architecture

## Overview
The Lenny Growth Assistant is a full-stack application composed of:
1.  **Frontend (React/Vite):** User interface for chat and secure artifact rendering.
2.  **Backend (FastAPI):** API Server, Agent orchestration, and RAG execution.
3.  **Database (PostgreSQL + pgvector):** Persistence for sessions, messages, artifacts, and embeddings.
4.  **LLM Provider (Ollama / Anthropic):** The inference engine.

## Phase 2: Knowledge Base & RAG Architecture
- **Transcript Data Flow:** Raw markdown files are downloaded from the public repository and placed in `data/transcripts/`. The `IngestionService` computes a SHA-256 hash to ensure idempotency. Unchanged files are skipped, whereas modified ones have their old chunks replaced.
- **Database Schema:** Two core tables are introduced: `TranscriptSource` for document-level metadata (episode title, guest name) and `TranscriptChunk` for individual text segments.
- **Chunking Strategy:** `DocumentChunker` utilizes `tiktoken` to chunk text with a target size of 600 tokens and an overlap of 100 tokens, respecting paragraph boundaries (`\n\n`) whenever possible to maintain semantic cohesion.
- **Embedding Architecture:** Embeddings are generated using the local Ollama API running the `nomic-embed-text` model. The resulting 768-dimensional vectors are stored in PostgreSQL utilizing the `pgvector` extension.
- **Vector Retrieval:** `TranscriptRetriever` handles semantic search. The `cosine_distance` (`<=>`) operator is used for nearest-neighbor search. 
- **Similarity Threshold:** A configurable threshold (default 0.5) ensures that `has_relevant_context` is explicitly set to `False` if no results meet the minimum relevance. This prevents hallucinated answers based on weak context.
- **Source Traceability:** Every chunk maintains a direct relation to its source. The retriever contract guarantees that `source_id`, `episode_title`, and URL metadata are bubbled up to the agent layer for explicit citation.

## Database Schema
- `User`: Lightweight identity.
- `Session`: Chat session metadata, linked to a User.
- `Message`: Chat history, linked to a Session.
- `Artifact`: Generated content (MD/HTML), linked to a Message.
- `TranscriptChunk`: Text chunk, embedding vector, and source metadata (episode, URL, hash).

## RAG Flow
1. User queries the system.
2. Backend embeds query using local embedding model.
3. Cosine similarity search against `TranscriptChunk` in `pgvector`.
4. If results < threshold, return "No relevant information found".
5. Otherwise, inject top-K chunks (with metadata) into LLM context.
6. LLM generates grounded answer with citations.

## LLM Provider Abstraction
An abstract `LLMProvider` interface defines `generate` and `stream` methods.
`OllamaProvider` and `AnthropicProvider` implement this interface. The app configuration (`LLM_PROVIDER`) dictates which provider is instantiated at runtime.

## Agent SDK Integration
We use the Anthropic Claude Agent SDK for orchestration. To support Ollama, our `LLMProvider` implementation for Ollama translates the SDK's expected prompt/tool structures into the Ollama API format, maintaining a clean boundary.

## Artifact Security
HTML artifacts are rendered in an `<iframe>` with `sandbox=""` to prevent JS execution and external resource loading. Markdown is sanitized client-side.
