# Implementation Plan: The Lenny Growth Assistant

This document outlines the proposed implementation plan for the "Lenny Growth Assistant" full-stack AI conversational web application, incorporating the specific evaluation rubric requirements.

## 1. Agent SDK Requirement
*   The agent layer will be built using the **Anthropic Claude Agent SDK**.
*   **Limitation & Abstraction Strategy:** The Anthropic SDK is natively designed around Anthropic's API and message structures. To support the mandatory Ollama requirement without polluting business logic, we will separate agent orchestration from the LLM execution layer. We will implement an adapter that translates Anthropic SDK tool-calling structures to Ollama's format (or rely on a clean `LLMProvider` abstraction that wraps both, mapping standard conversational structures to the provider's native format). The business layer will strictly depend on the Anthropic SDK orchestration, and the LLM execution will go through the `LLMProvider`.

## 2. LLM Provider Abstraction
```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[dict], tools: List[dict] = None) -> Any:
        pass

class OllamaProvider(LLMProvider): ...
class AnthropicProvider(LLMProvider): ...
```
The application will instantiate the concrete class based on the `LLM_PROVIDER` environment variable (default: `ollama`). No provider-specific branching will exist in the application logic.

## 3. Real Transcript Data
We will not fabricate data. We will source a subset of publicly available Lenny's Podcast transcripts.
*   **Ingestion Strategy:** Raw text/markdown transcripts will be stored in `data/transcripts/`.
*   A CLI ingestion script (not an API endpoint) will process these files safely. It will handle idempotency (prevent duplicate insertions) by computing a `content_hash` for each file and checking existing database records.

## 4. Transcript Schema
The `TranscriptChunk` database schema will preserve comprehensive source metadata for accurate citations:
*   `id` (UUID)
*   `source_id` (String - e.g., filename or episode ID)
*   `episode_title` (String)
*   `guest_name` (String, optional)
*   `source_url` (String, optional)
*   `transcript_url` (String, optional)
*   `chunk_index` (Integer)
*   `text` (Text)
*   `embedding` (Vector)
*   `ingestion_timestamp` (DateTime)
*   `content_hash` (String - for idempotency)

## 5. User Metadata
A lightweight identity model will be implemented:
*   `User`: `id` (UUID), `metadata` (JSON - non-sensitive preferences/info), `created_at`
*   `Session`: `id` (UUID), `user_id` (FK), `title`, `created_at`

## 6. Session Isolation
Every session has strictly independent context.
*   The backend derives history solely from the database using the `session_id`.
*   Tests will explicitly assert that messages from Session A are inaccessible when processing Session B.

## 7. Artifact Security
Generated HTML will be treated as untrusted and malicious.
*   **Sanitization:** Strict sanitization (e.g., DOMPurify or `rehype-sanitize`) will remove dangerous event handlers, `javascript:` URLs, and external resource loading.
*   **Rendering:** Artifacts will be rendered in an isolated `<iframe>` using the `sandbox=""` attribute (disallowing scripts entirely for initial static HTML/CSS).
*   **Testing:** Malicious payload tests will be included.

## 8. Ingestion Endpoint Security
There will be **no public or unauthenticated API endpoint** for ingestion.
*   Ingestion will be triggered exclusively via a CLI command (e.g., `python scripts/ingest.py`) designed for local development and CI/CD environments.

## 9. Testing Architecture
*   **Dependency Injection:** LLM calls will be mocked using a `MockProvider(LLMProvider)` for fast, deterministic unit tests without network or API dependencies.
*   **Coverage Targets:** Session creation/isolation, message persistence, retrieval/empty behavior, provider routing, configuration parsing, DB failure handling, artifact sanitization.
*   **Integration Tests:** A limited set of tests will run against a local PostgreSQL + pgvector instance to verify DB behavior.

## 10. RAG Grounding Flow
Grounding is enforced explicitly in application logic, not just system prompts:
1.  **User Question** -> `SearchTranscripts` tool.
2.  **Retrieval** -> Vector search with a similarity threshold.
3.  **Relevance Check** -> If results are empty or below threshold, the agent receives an explicit "No relevant information found" signal.
4.  **Agent Logic** -> The agent is programmed to output: "I couldn't find enough information in the Lenny corpus..." rather than hallucinating.
5.  **Answer** -> Includes explicit source references (e.g., "Source: Lenny's Podcast — [Episode Title], [Guest]").

## 11. Observability
Structured logging (e.g., using `structlog`) will include:
`request_id`, `session_id`, `llm_provider`, `model`, `retrieval_count`, `retrieval_latency`, `llm_latency`.
API keys and sensitive user text will be strictly excluded from logs.

## 12. Documentation Deliverables
The following will be provided as first-class deliverables:
*   `README.md`
*   `docs/PRD.md` (Including Forward Deployment Brief)
*   `docs/design.md`
*   `docs/architecture.md`
*   `docs/test_plan.md`
*   `agent-transcripts/` (Logs of agent attempts)

## 13. Implementation Phases

**Phase 1: Foundation (Current Target)**
*   Project structure, Docker Compose (PostgreSQL, pgvector, Ollama), FastApi + React setup.
*   Database migrations & health endpoints.
*   Basic structured logging and tests.
*   Documentation skeletons.

*(Subsequent phases omitted for brevity but remain as previously structured: RAG/Ingestion -> Agent/LLM Core -> API/Artifacts -> UI/Polish).*
