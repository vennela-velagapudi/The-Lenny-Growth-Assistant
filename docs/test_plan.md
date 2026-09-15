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

## Manual Verification
1.  **Setup:** Run `docker compose up`, verify all 4 containers start.
2.  **Ollama Demo:** Ask a question, verify local inference works.
3.  **Provider Switch:** Change `.env` to `Anthropic`, restart, verify cloud inference works.
4.  **RAG Grounding:** Ask about a topic *not* in Lenny's podcast. Verify the system explicitly refuses to answer or states lack of evidence.
5.  **Citations:** Ask a covered topic. Verify the response includes a citation (e.g., "Source: Lenny's Podcast — Episode 1").
6.  **Security:** Request a malicious HTML artifact with an alert. Verify the alert does not fire when rendered.
