# Architecture

## Overview
The Lenny Growth Assistant is a full-stack application composed of:
1.  **Frontend (React/Vite):** User interface for chat and secure artifact rendering.
2.  **Backend (FastAPI):** API Server, Agent orchestration, and RAG execution.
3.  **Database (PostgreSQL + pgvector):** Persistence for sessions, messages, artifacts, and embeddings.
4.  **LLM Provider (Ollama / Anthropic):** The inference engine.

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
