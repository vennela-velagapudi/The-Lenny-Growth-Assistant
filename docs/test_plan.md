# Test Plan

## Automated Testing (Pytest)
- **Unit Tests:**
  - `LLMProvider` routing and configuration parsing.
  - RAG prompt construction and empty-result handling.
  - HTML artifact sanitization logic.
- **Integration Tests:**
  - FastAPI endpoints (session creation, message history).
  - PostgreSQL/pgvector insertion and retrieval.
  - Session isolation (User A cannot see User B's messages).

## Phase 2: Knowledge Base
### Automated Tests
- **Chunking Logic**: Unit tests to verify correct token sizes, overlaps, and handling of paragraph breaks. (Implemented in `test_chunker.py`)
- **Idempotency**: Unit tests to verify that identical hashes are skipped during ingestion. (Implemented in `test_ingestion.py`)
- **Retrieval Contract**: Unit tests to verify similarity threshold masking and `has_relevant_context` boolean. (Implemented in `test_retriever.py`)
- **Integration**: Verifies pgvector is queryable (`<=>` operator works). (Implemented in `test_db.py`, skippable if DB missing).

### Manual Tests
1. Obtain real transcripts (e.g., using `scripts/download_samples.py`) and run `python scripts/ingest.py`. Verify logs output positive chunk counts.
2. Re-run `python scripts/ingest.py` and verify `Skipped unchanged` equals the number of files.

## Phase 3: Conversational Agent
### Automated Tests
- **Provider Switching**: Tests ensure that `LLM_PROVIDER` routes requests strictly to Anthropic or Ollama based on configs. (Implemented in `test_agent.py`).
- **Grounding Interception**: Unit tests mock the retriever returning `has_relevant_context=False` to verify the deterministic "insufficient evidence" cutoff. (Implemented in `test_agent.py`).
- **Missing Keys**: Tests validating graceful exception on missing API credentials.
- **Session API contracts**: E2E test client validates session isolation and conversational state storage. (Implemented in `test_sessions_api.py`).

### Manual Tests
1. Setup Ollama. Send `POST /api/sessions` to get ID. Send message with specific podcast fact, observe retrieved chunks and grounding.
2. Swap to Anthropic in `.env`. Send identical queries. Validate Agent SDK execution.
1.  **Setup:** Run `docker compose up`, verify all 4 containers start.
2.  **Ollama Demo:** Ask a question, verify local inference works.
3.  **Provider Switch:** Change `.env` to `Anthropic`, restart, verify cloud inference works.
4.  **RAG Grounding:** Ask about a topic *not* in Lenny's podcast. Verify the system explicitly refuses to answer or states lack of evidence.
5.  **Citations:** Ask a covered topic. Verify the response includes a citation (e.g., "Source: Lenny's Podcast — Episode 1").
6.  **Security:** Request a malicious HTML artifact with an alert. Verify the alert does not fire when rendered.


## Phase 4 Additions
- Ship 30 Skill: Deterministic intent routing directs requests for 'Ship 30' pieces into a dedicated skill module.
- Artifact Generation: Artifacts (Markdown, HTML) are generated via specialized prompts, tracked, and stored in PostgreSQL.
- UI & Viewer: React frontend split layout with interactive chat and side-by-side artifact viewer.
- Security: HTML artifacts are sanitized via DOMPurify and placed inside a sandboxed iframe to prevent JS execution or DOM escape.

